import { useState, useEffect, useRef } from "react";

import Div from "@/baseComponents/reusableComponents/Div";

import ConnectionToSocket from "./subs/ConnectionToSocket";
import ChatBox from "./subs/ChatBox";
const Dashboard = () => {
  const socketRefManager = useRef();
  return (
    <>
      <ConnectionToSocket socketRefManager={socketRefManager}>
        <ChatBox socketRefManager={socketRefManager} />
      </ConnectionToSocket>
    </>
  );
};

export default Dashboard;
