import Div from "@/baseComponents/reusableComponents/Div";
import Icon from "@/baseComponents/reusableComponents/Icon";

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
        type="flex"
        direction="vertical"
        vAlign="center"
        className="p-x-16 br-all-solid-2 br-rad-px-10 height-px-200 width-per-100 of-x-auto"
      >
        <Div
          ref={containerRef}
          type="flex"
          vAlign="center"
          className=""
          style={{
            width: remoteFeeds?.length ? (remoteFeeds?.length + 1) * 100 : 100,
          }}
        >
          <Div className="br-all-solid-2 br-green height-px-100 of-hidden width-px-100 br-rad-per-50">
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
              className="br-all-solid-2 br-red height-px-100 of-hidden width-px-100 br-rad-per-50"
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

        <Div type="flex" hAlign="center" className="m-t-16 width-per-100">
          <Div
            type="flex"
            hAlign="center"
            vAlign="center"
            className="m-r-16 height-px-30 width-px-30 mouse-hand"
            onClick={toggleAudio}
          >
            <Icon
              type={audioEnabled ? "microphone" : "microphone-slash"}
              scale={1.5}
            />
          </Div>
          <Div
            type="flex"
            hAlign="center"
            vAlign="center"
            className="m-r-16 height-px-30 width-px-30 mouse-hand"
            onClick={toggleRemoteAudio}
          >
            <Icon
              type={allMuted ? "volume-xmark" : "volume-high"}
              scale={1.5}
            />
          </Div>
          <Div
            type="flex"
            hAlign="center"
            vAlign="center"
            className="height-px-30 width-px-30 mouse-hand"
            onClick={toggleVideo}
          >
            <Icon type={videoEnabled ? "video" : "video-slash"} scale={1.5} />
          </Div>
        </Div>

        {/* <Div className="m-all-32">
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
      </Div> */}
      </Div>
    </>
  );
};

export default Streaming;
