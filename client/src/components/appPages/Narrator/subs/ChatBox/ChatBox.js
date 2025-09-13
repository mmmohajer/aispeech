import { useState, useEffect, useRef } from "react";

import BaseChatBox from "@/baseComponents/reusableComponents/ChatBox";
import Div from "@/baseComponents/reusableComponents/Div";
import Typing from "@/baseComponents/reusableComponents/Typing";

const ChatBox = ({
  socketRefManager,
  slides,
  speech,
  showLoader,
  setShowLoader,
}) => {
  const [goBottomOfTheContainer, setGoBottomOfTheContainer] = useState(true);
  const [displayedSlides, setDisplayedSlides] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [fullAudio, setFullAudio] = useState(null);
  const [curUserMessage, setCurUserMessage] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  // Use a ref so updating the seen set does NOT cause re-renders / re-scheduling
  const seenKeysRef = useRef(new Set());
  // Keep a ref of active timers to clean up on new batches/unmount
  const activeTimersRef = useRef([]);

  // ----------------------------------------------------------------
  // Handle new batches of slides (no duplicates, no timing drift)
  // ----------------------------------------------------------------
  useEffect(() => {
    if (!slides || slides.length === 0) return;

    // clear any previous timers for safety when a new batch arrives
    activeTimersRef.current.forEach(clearTimeout);
    activeTimersRef.current = [];

    const latestBatch = slides[slides.length - 1];
    if (!latestBatch || latestBatch.length === 0) return;

    // Fresh clock per batch
    const roundStart = performance.now();

    latestBatch.forEach((slide) => {
      const t = Number(slide?.start_time_to_display_slide_content || 0);
      const key = `${t}-${slide.content}`;

      // If we already scheduled/shown this exact slide, skip
      if (seenKeysRef.current.has(key)) return;

      // PRE-MARK as scheduled to avoid re-scheduling if this effect re-runs
      seenKeysRef.current.add(key);

      // Schedule relative to batch arrival
      const delayMs = Math.max(0, t * 1000 - (performance.now() - roundStart));

      const timer = setTimeout(() => {
        const elapsedSec = ((performance.now() - roundStart) / 1000).toFixed(2);
        setDisplayedSlides((prev) => [...prev, slide]);
        setGoBottomOfTheContainer(true);
      }, delayMs);

      activeTimersRef.current.push(timer);
    });

    // Cleanup timers if component unmounts or a new batch arrives
    return () => {
      activeTimersRef.current.forEach(clearTimeout);
      activeTimersRef.current = [];
    };
  }, [slides]); // <-- IMPORTANT: only depends on slides

  // ----------------------------------------------------------------
  // Auto-play audio when speech changes
  // ----------------------------------------------------------------
  useEffect(() => {
    if (speech) {
      const audio = new window.Audio(`data:audio/wav;base64,${speech}`);
      audio.play();
    }
  }, [speech]);

  // ----------------------------------------------------------------
  // Recording chunks sending to backend
  // ----------------------------------------------------------------
  const handleChunk = (chunk) => {
    setChunks((prev) => [...prev, chunk]);
  };

  useEffect(() => {
    if (chunks.length === 0) return;

    if (socketRefManager?.current?.send) {
      const combinedBlob = new Blob(chunks, { type: "audio/webm" });
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result.split(",")[1];
        const message = {
          task: "listen_to_audio",
          chunk_id: chunks.length,
          voice_chunk: base64,
          is_last_chunk: !isRecording,
        };
        socketRefManager.current.send(JSON.stringify(message));
        if (!isRecording) {
          setChunks([]);
        }
      };
      reader.readAsDataURL(combinedBlob);
    }
  }, [chunks, isRecording, socketRefManager]);

  // ----------------------------------------------------------------
  // Always scroll to bottom when a new slide is displayed
  // ----------------------------------------------------------------
  useEffect(() => {
    setGoBottomOfTheContainer(true);
  }, [displayedSlides]);

  return (
    <>
      <BaseChatBox
        goBottomOfTheContainer={goBottomOfTheContainer}
        setGoBottomOfTheContainer={setGoBottomOfTheContainer}
        userChatMessage={curUserMessage}
        setUserChatMessage={setCurUserMessage}
        handleChunk={handleChunk}
        handleAudioComplete={(blob) => {
          setFullAudio(blob);
          setShowLoader(true);
        }}
        showLoader={showLoader}
        setIsRecording={setIsRecording}
        mainContainerClassName="flex--grow--1 bg-white"
      >
        {displayedSlides.map((slide, idx) => (
          <Div key={idx}>
            <Typing
              htmlContent={slide.content}
              speed={20}
              callBackFunction={() => setGoBottomOfTheContainer(true)}
            />
          </Div>
        ))}
      </BaseChatBox>
    </>
  );
};

export default ChatBox;
