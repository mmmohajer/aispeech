import Div from "@/baseComponents/reusableComponents/Div";

import useDivWidth from "@/hooks/useDivWidth";
import useStreaming from "@/hooks/useStreaming";

const Streaming = ({ roomId }) => {
  const {
    localVideoRef,
    remoteFeeds,
    audioEnabled,
    videoEnabled,
    toggleAudio,
    toggleVideo,
    allMuted,
    toggleRemoteAudio,
  } = useStreaming({ roomId });
  const { containerRef, width } = useDivWidth();

  return (
    <>
      <Div
        ref={containerRef}
        type="flex"
        vAlign="center"
        className="width-per-100 flex--wrap"
      >
        <Div className="br-all-solid-2 br-green height-px-100 of-hidden br-rad-px-10">
          <video
            ref={localVideoRef}
            autoPlay
            muted
            playsInline
            style={{
              height: `100px`,
            }}
          />
        </Div>

        {remoteFeeds.map(({ id, stream }) => (
          <Div
            key={id}
            className="br-all-solid-2 br-red height-px-100 of-hidden br-rad-px-10"
          >
            <video
              autoPlay
              playsInline
              style={{
                height: `100px`,
              }}
              ref={(el) => {
                if (el && stream && el.srcObject !== stream)
                  el.srcObject = stream;
              }}
            />
          </Div>
        ))}
      </Div>
      <Div className="m-all-32">
        <button onClick={toggleAudio} className="m-r-16">
          {audioEnabled ? "Mute" : "Unmute"}
        </button>
        <button onClick={toggleVideo}>
          {videoEnabled ? "Hide Video" : "Show Video"}
        </button>
      </Div>

      <Div className="m-all-32">
        <button onClick={toggleRemoteAudio} className="m-r-16">
          {allMuted ? "Unmute All Voices" : "Mute All Voices"}
        </button>
      </Div>
    </>
  );
};

export default Streaming;
