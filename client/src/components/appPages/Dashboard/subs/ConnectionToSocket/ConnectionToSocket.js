import { useState, useEffect } from "react";

import Div from "@/baseComponents/reusableComponents/Div";

import useWebSocket from "@/hooks/useWebSocket";
import { CHAT_BOT_API_ROUTE } from "@/constants/apiRoutes";

import { handleMessage } from "./utils";

const ConnectionToSocket = ({ socketRefManager, children }) => {
  // -------------------------------------------------
  // Chat Socket Request Handler Start
  // -------------------------------------------------
  const [sendReq, setSendReq] = useState(false);
  const { socketRef, send } = useWebSocket({
    sendReq,
    setSendReq,
    url: `${CHAT_BOT_API_ROUTE}`,
    onMessage: (event) => handleMessage(event),
  });
  useEffect(() => {
    setSendReq(true);
  }, []);
  useEffect(() => {
    if (socketRef && send) {
      socketRefManager.current = { ref: socketRef, send: send };
    }
  }, [socketRef, send]);
  // -------------------------------------------------
  // Chat Socket Request Handler End
  // -------------------------------------------------
  return <>{children}</>;
};

export default ConnectionToSocket;
