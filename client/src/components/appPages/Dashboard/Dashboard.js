import { useState, useEffect, useRef } from "react";

import Div from "@/baseComponents/reusableComponents/Div";

import ConnectionToSocket from "./subs/ConnectionToSocket";
import ChatBox from "./subs/ChatBox";
import { handleWsData } from "./utils";
const Dashboard = () => {
  const socketRefManager = useRef();

  const [wsData, setWsData] = useState({});

  useEffect(() => {
    handleWsData(socketRefManager, wsData);
  }, [wsData]);

  return (
    <>
      <ConnectionToSocket
        socketRefManager={socketRefManager}
        setWsData={setWsData}
      >
        <ChatBox socketRefManager={socketRefManager} wsData={wsData} />
      </ConnectionToSocket>
    </>
  );
};

export default Dashboard;
