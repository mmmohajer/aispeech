import { useState, useEffect, useRef } from "react";

import Div from "@/baseComponents/reusableComponents/Div";

import ConnectionToSocket from "./subs/ConnectionToSocket";
import ChatBox from "./subs/ChatBox";
import WaitingForClassToStart from "./subs/WaitingForClassToStart";
import { handleWsData } from "./utils";
const Dashboard = () => {
  const socketRefManager = useRef();

  const [classStarted, setClassStarted] = useState(false);
  const [wsData, setWsData] = useState({});
  const [slides, setSlides] = useState([]);
  const [speech, setSpeech] = useState("");
  const [showLoader, setShowLoader] = useState(true);

  useEffect(() => {
    handleWsData(socketRefManager, wsData, setSlides, setSpeech, setShowLoader);
  }, [wsData]);

  return (
    <>
      <ConnectionToSocket
        socketRefManager={socketRefManager}
        setWsData={setWsData}
        classStarted={classStarted}
      >
        {classStarted ? (
          <ChatBox
            socketRefManager={socketRefManager}
            wsData={wsData}
            slides={slides}
            speech={speech}
            showLoader={showLoader}
            setShowLoader={setShowLoader}
          />
        ) : (
          <WaitingForClassToStart setClassStarted={setClassStarted} />
        )}
      </ConnectionToSocket>
    </>
  );
};

export default Dashboard;
