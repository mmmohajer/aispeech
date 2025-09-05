"use client";
import { useEffect, useRef, useState } from "react";

export default function VoiceStreaming({ roomId = 1234 }) {
  const localVideo = useRef(null);
  const startedRef = useRef(false);
  const [remoteFeeds, setRemoteFeeds] = useState([]); // [{ id: feedId, stream }]
  const remoteHandlesRef = useRef({});
  const remoteStreamsRef = useRef({}); // feedId -> MediaStream
  const feedMidsRef = useRef({});

  const ICE_SERVERS = [
    { urls: "stun:stun.l.google.com:19302" },
    {
      urls: "turn:192.168.2.76:3478?transport=udp",
      username: "webrtcuser",
      credential: "webrtccred",
    },
  ];

  const JANUS_SERVER = "wss://makeclient.ngrok.io/janus";

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

                // Capture and publish
                navigator.mediaDevices
                  .getUserMedia({ video: true, audio: true })
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
                  (msg.publishers || []).forEach((p) => {
                    feedMidsRef.current[p.id] = extractMids(p);
                    subscribeToFeed(p.id);
                  });
                }

                if (evt === "event") {
                  if (msg.publishers) {
                    msg.publishers.forEach((p) => {
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

              webrtcState: (on) =>
                console.log("📶 Publisher WebRTC state:", on),
              iceState: (state) =>
                console.log("🧊 Publisher ICE state:", state),
              error: (err) => console.error("❌ Publisher attach error:", err),
            });
          },
          error: (err) => console.error("❌ Janus init error:", err),
        });
      },
    });

    // ---- SUBSCRIBER (old-style join with feed) ----
    const subscribeToFeed = (feedId) => {
      if (!janus) return;
      if (remoteHandlesRef.current[feedId]) return;

      janus.attach({
        plugin: "janus.plugin.videoroom",
        success: (sub) => {
          remoteHandlesRef.current[feedId] = sub;

          // Join as subscriber to that feed
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

          // Answer Janus' offer, then start
          if (jsep && jsep.type === "offer") {
            const sub = remoteHandlesRef.current[feedId];
            if (!sub) return;
            sub.createAnswer({
              jsep,
              media: { audioSend: false, videoSend: false },
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

        // ✅ Merge audio+video into ONE stream per feed
        onremotetrack: (track, mid, on) => {
          let stream = remoteStreamsRef.current[feedId];

          if (!on) {
            if (stream) {
              stream.getTracks().forEach((t) => {
                if (t.id === track.id) stream.removeTrack(t);
              });
              if (stream.getTracks().length === 0) cleanupFeed(feedId);
              else setRemoteFeeds((prev) => [...prev]); // re-render after removal
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
            setRemoteFeeds((prev) => [...prev]); // <— force re-render so hasVideo updates
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
        webrtcState: (on) => console.log("📶 Subscriber WebRTC state:", on),
        iceState: (state) => console.log("🧊 Subscriber ICE state:", state),
        error: (err) => console.error("❌ Subscriber attach error:", err),
      });
    };

    const cleanupFeed = (feedId) => {
      console.log("🧹 Cleanup feed", feedId);
      // remove tile
      setRemoteFeeds((prev) => prev.filter((f) => f.id !== String(feedId)));
      // stop & drop stream
      const stream = remoteStreamsRef.current[feedId];
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        delete remoteStreamsRef.current[feedId];
      }
      // detach handle
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

  useEffect(() => {
    console.log("Hello");
    console.log("📺 Remote feeds updated:", remoteFeeds);
  }, [remoteFeeds]);

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

      {/* Remotes: one element per feed */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {remoteFeeds.map(({ id, stream }) => {
          const hasVideo = stream?.getVideoTracks?.().length > 0;
          console.log("Feed", id, "hasVideo?", hasVideo);

          if (!hasVideo) return null; // hide empty tiles until video is present

          return (
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
          );
        })}
      </div>
    </div>
  );
}
