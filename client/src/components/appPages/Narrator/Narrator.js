import { useState, useEffect, useRef } from "react";

import Div from "@/baseComponents/reusableComponents/Div";

import ConnectionToSocket from "./subs/ConnectionToSocket";
import ChatBox from "./subs/ChatBox";
import Streaming from "./subs/Streaming";

const Narrator = ({ roomId = 123456 }) => {
  const socketRefManager = useRef();

  const [sendWsReq, setSendWsReq] = useState(false);
  const [wsData, setWsData] = useState({});
  const [slides, setSlides] = useState([]);
  const [speech, setSpeech] = useState("");
  const [showLoader, setShowLoader] = useState(true);

  return (
    <>
      <ConnectionToSocket
        socketRefManager={socketRefManager}
        wsData={wsData}
        setWsData={setWsData}
        sendWsReq={sendWsReq}
        setSendWsReq={setSendWsReq}
        setSlides={setSlides}
        setSpeech={setSpeech}
        setShowLoader={setShowLoader}
        roomId={roomId}
      />
      {wsData?.connection ? (
        <Div
          type="flex"
          direction="vertical"
          className="p-all-16 height-vh-full"
        >
          <Streaming roomId={roomId} />
          <ChatBox
            socketRefManager={socketRefManager}
            wsData={wsData}
            slides={slides}
            speech={speech}
            showLoader={showLoader}
            setShowLoader={setShowLoader}
          />
        </Div>
      ) : null}
    </>
  );
};

export default Narrator;
