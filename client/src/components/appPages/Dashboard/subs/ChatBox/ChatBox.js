import { useState, useEffect } from "react";
import cx from "classnames";

import Div from "@/baseComponents/reusableComponents/Div";
import Button from "@/baseComponents/reusableComponents/Button";
import VoiceRecorder from "@/baseComponents/reusableComponents/VoiceRecorder";
import Icon from "@/baseComponents/reusableComponents/Icon";
import TextBox from "@/baseComponents/formComponents/TextBox";
import AreaText from "@/baseComponents/formComponents/AreaText";

import styles from "./ChatBox.module.scss";

const ChatBox = ({ socketRefManager }) => {
  const [chunks, setChunks] = useState([]);
  const [fullAudio, setFullAudio] = useState(null);
  const [recording, setRecording] = useState(false);
  const [curUserMessage, setCurUserMessage] = useState("");

  return (
    <>
      <Div
        type="flex"
        direction="vertical"
        className="height-vh-full width-per-100 p-all-16"
      >
        <Div
          type="flex"
          direction="vertical"
          className="flex--grow--1 b br-all-solid-2 br-rad-px-10 br--black width-per-100"
        >
          <Div className="width-per-100 flex--grow--1 p-all-16"></Div>
          <Div
            type="flex"
            vAlign="center"
            className="width-per-100 flex--shrink--0 height-px-100 br-top-solid-2 br-black"
          >
            <Div type="flex" className="width-per-100">
              <Div className="flex--grow--1">
                <AreaText
                  placeHolder="Type your message..."
                  value={curUserMessage}
                  onChange={(e) => setCurUserMessage(e.target.value)}
                  disabled={recording}
                />
              </Div>
              <Div>
                <VoiceRecorder
                  onChunk={(chunk) => {
                    setChunks((prev) => {
                      const updatedChunks = [...prev, chunk];
                      if (socketRefManager?.current?.send) {
                        const combinedBlob = new Blob(updatedChunks, {
                          type: "audio/webm",
                        });
                        const reader = new FileReader();
                        reader.onload = () => {
                          const base64 = reader.result.split(",")[1];
                          const message = {
                            type: "audio",
                            chunk_id: updatedChunks.length - 1,
                            voice_chunk: base64,
                            total_chunks: updatedChunks.length,
                          };
                          socketRefManager.current.send(
                            JSON.stringify(message)
                          );
                        };
                        reader.readAsDataURL(combinedBlob);
                      }
                      return updatedChunks;
                    });
                  }}
                  onComplete={(blob) => setFullAudio(blob)}
                  // onComplete={(blob) => {
                  //   setFullAudio(blob);
                  //   if (socketRefManager?.current?.send) {
                  //     const reader = new FileReader();
                  //     reader.onload = () => {
                  //       const base64 = reader.result.split(",")[1]; // Remove data URL prefix
                  //       const message = {
                  //         type: "audio",
                  //         chunk_id: Date.now(), // or any unique id
                  //         voice_chunk: base64,
                  //         is_final: true, // optional flag to indicate completion
                  //       };
                  //       socketRefManager.current.send(JSON.stringify(message));
                  //     };
                  //     reader.readAsDataURL(blob);
                  //   }
                  // }}
                  recording={recording}
                  setRecording={setRecording}
                  chunkDurationInSecond={60}
                />
              </Div>
              <Div type="flex" vAlign="center">
                <Div
                  type="flex"
                  hAlign="center"
                  vAlign="center"
                  // onClick={() => setRecording(!recording)}
                  className={cx("width-px-50 height-px-50")}
                >
                  <Icon
                    type={"paper-plane"}
                    scale={2}
                    color={recording ? "gray" : "black"}
                  />
                </Div>
                <Div
                  type="flex"
                  hAlign="center"
                  vAlign="center"
                  onClick={() => setRecording(!recording)}
                  className={cx(
                    "width-px-50 height-px-50",
                    styles.microphoneContainer,
                    { [styles.recording]: recording }
                  )}
                >
                  <Icon
                    type={recording ? "stop-circle" : "microphone"}
                    scale={2}
                    color="black"
                  />
                </Div>
              </Div>
            </Div>
          </Div>
        </Div>
      </Div>
    </>
  );
};

export default ChatBox;
