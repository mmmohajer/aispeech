"use client";
import { useEffect, useRef, useState } from "react";

import { ICE_SERVER_DOMAIN, APP_DOMAIN } from "config";

export default function VoiceStreaming({ roomId = 1234 }) {
  const localVideo = useRef(null);
  const startedRef = useRef(false);
  const [remoteFeeds, setRemoteFeeds] = useState([]); // [{ id: feedId, stream }]
  const remoteHandlesRef = useRef({});
  const remoteStreamsRef = useRef({}); // feedId -> MediaStream
  const feedMidsRef = useRef({});
  const myIdRef = useRef(null); // 👈 store my publisher ID

  const ICE_SERVERS = [
    { urls: "stun:stun.l.google.com:19302" },
    {
      urls: `turn:${ICE_SERVER_DOMAIN}:3478?transport=udp`,
      username: "webrtcuser",
      credential: "webrtccred",
    },
  ];

  const JANUS_SERVER = `wss://${APP_DOMAIN}/janus`;

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    if (!window.Janus) {
      console.error("❌ Janus.js not loaded");
      return;
    }

    let janus = null;
    let pub = null;

    const extractMids = (publisher) => {
      const mids = (publisher?.streams || [])
        .filter((s) => s.type === "video" || s.type === "audio")
        .map((s) => s.mid?.toString())
        .filter(Boolean);
      return mids.length ? mids : ["0", "1"];
    };

    window.Janus.init({
      debug: ["error"],
      callback: () => {
        janus = new window.Janus({
          server: JANUS_SERVER,
          iceServers: ICE_SERVERS,
          success: () => {
            // ---- PUBLISHER ----
            janus.attach({
              plugin: "janus.plugin.videoroom",
              success: (handle) => {
                pub = handle;

                // Join as publisher
                pub.send({
                  message: {
                    request: "join",
                    room: roomId,
                    ptype: "publisher",
                    display: `user-${Math.floor(Math.random() * 1000)}`,
                  },
                });

                // Capture and publish with echo cancellation
                navigator.mediaDevices
                  .getUserMedia({
                    video: true,
                    audio: { echoCancellation: true, noiseSuppression: true },
                  })
                  .then((stream) => {
                    if (localVideo.current)
                      localVideo.current.srcObject = stream;
                    pub.createOffer({
                      media: { audio: true, video: true },
                      trickle: true,
                      success: (jsep) =>
                        pub.send({ message: { request: "publish" }, jsep }),
                      error: (err) =>
                        console.error("❌ Publisher createOffer error:", err),
                    });
                  })
                  .catch((e) => console.error("❌ getUserMedia failed:", e));
              },

              onmessage: (msg, jsep) => {
                const evt = msg.videoroom;

                if (evt === "joined") {
                  myIdRef.current = msg.id; // 👈 save my ID
                  console.log(
                    "✅ Joined room",
                    roomId,
                    "with ID",
                    myIdRef.current
                  );

                  // Subscribe to existing publishers (skip self)
                  (msg.publishers || []).forEach((p) => {
                    if (p.id === myIdRef.current) return; // skip myself
                    feedMidsRef.current[p.id] = extractMids(p);
                    subscribeToFeed(p.id);
                  });
                }

                if (evt === "event") {
                  if (msg.publishers) {
                    msg.publishers.forEach((p) => {
                      if (p.id === myIdRef.current) return; // skip myself
                      feedMidsRef.current[p.id] = extractMids(p);
                      subscribeToFeed(p.id);
                    });
                  }
                  if (msg.unpublished || msg.leaving) {
                    const feedId = msg.unpublished || msg.leaving;
                    cleanupFeed(feedId);
                  }
                }

                if (jsep && jsep.type === "answer") {
                  pub.handleRemoteJsep({ jsep });
                }
              },

              error: (err) => console.error("❌ Publisher attach error:", err),
            });
          },
          error: (err) => console.error("❌ Janus init error:", err),
        });
      },
    });

    // ---- SUBSCRIBER ----
    const subscribeToFeed = (feedId) => {
      if (!janus) return;
      if (feedId === myIdRef.current) return; // 👈 don’t subscribe to myself
      if (remoteHandlesRef.current[feedId]) return;

      janus.attach({
        plugin: "janus.plugin.videoroom",
        success: (sub) => {
          remoteHandlesRef.current[feedId] = sub;

          sub.send({
            message: {
              request: "join",
              room: roomId,
              ptype: "subscriber",
              feed: feedId,
            },
          });
        },

        onmessage: (msg, jsep) => {
          const evt = msg.videoroom;

          if (evt === "attached") {
            console.log("👀 Subscriber attached to feed", feedId);
          }

          if (
            evt === "event" &&
            (msg.unpublished || msg.leaving || msg.error_code === 428)
          ) {
            cleanupFeed(feedId);
          }

          if (jsep && jsep.type === "offer") {
            const sub = remoteHandlesRef.current[feedId];
            if (!sub) return;
            sub.createAnswer({
              jsep,
              media: { audioSend: false, videoSend: false }, // don’t send audio back
              trickle: true,
              success: (jsepAnswer) => {
                sub.send({
                  message: { request: "start", room: roomId },
                  jsep: jsepAnswer,
                });
              },
              error: (err) =>
                console.error("❌ Subscriber createAnswer error:", err),
            });
          }
        },

        onremotetrack: (track, mid, on) => {
          let stream = remoteStreamsRef.current[feedId];

          if (!on) {
            if (stream) {
              stream.getTracks().forEach((t) => {
                if (t.id === track.id) stream.removeTrack(t);
              });
              if (stream.getTracks().length === 0) cleanupFeed(feedId);
              else setRemoteFeeds((prev) => [...prev]);
            }
            return;
          }

          if (!stream) {
            stream = new MediaStream();
            remoteStreamsRef.current[feedId] = stream;
            setRemoteFeeds((prev) =>
              prev.find((f) => f.id === String(feedId))
                ? prev
                : [...prev, { id: String(feedId), stream }]
            );
          }

          if (!stream.getTracks().some((t) => t.id === track.id)) {
            stream.addTrack(track);
            setRemoteFeeds((prev) => [...prev]);
          }

          console.log(
            "🎥 Got remote track:",
            track.kind,
            "feed",
            feedId,
            "mid",
            mid
          );
        },

        oncleanup: () => cleanupFeed(feedId),
        error: (err) => console.error("❌ Subscriber attach error:", err),
      });
    };

    const cleanupFeed = (feedId) => {
      console.log("🧹 Cleanup feed", feedId);
      setRemoteFeeds((prev) => prev.filter((f) => f.id !== String(feedId)));
      const stream = remoteStreamsRef.current[feedId];
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        delete remoteStreamsRef.current[feedId];
      }
      const sub = remoteHandlesRef.current[feedId];
      if (sub) {
        try {
          sub.hangup();
          sub.detach();
        } catch {}
        delete remoteHandlesRef.current[feedId];
      }
      delete feedMidsRef.current[feedId];
    };

    return () => {
      try {
        Object.keys(remoteHandlesRef.current).forEach((id) => {
          try {
            remoteHandlesRef.current[id].hangup();
            remoteHandlesRef.current[id].detach();
          } catch {}
        });
        Object.values(remoteStreamsRef.current).forEach((s) =>
          s.getTracks().forEach((t) => t.stop())
        );
        pub?.hangup?.();
        pub?.detach?.();
        janus?.destroy?.();
      } catch {}
    };
  }, [roomId]);

  return (
    <div>
      <h3>Room {roomId}</h3>

      {/* Local */}
      <video
        ref={localVideo}
        autoPlay
        muted
        playsInline
        style={{ width: 300, border: "2px solid green" }}
      />

      {/* Remotes */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {remoteFeeds.map(({ id, stream }) => (
          <video
            key={id}
            autoPlay
            playsInline
            style={{ width: 300, border: "2px solid red" }}
            ref={(el) => {
              if (el && stream && el.srcObject !== stream)
                el.srcObject = stream;
            }}
          />
        ))}
      </div>
    </div>
  );
}
