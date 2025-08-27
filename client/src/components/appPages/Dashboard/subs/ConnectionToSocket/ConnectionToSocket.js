import { useState, useEffect } from "react";
import { useSelector } from "react-redux";

import Div from "@/baseComponents/reusableComponents/Div";

import useWebSocket from "@/hooks/useWebSocket";
import { CHAT_BOT_API_ROUTE, TEACHER_API_ROUTE } from "@/constants/apiRoutes";

const ConnectionToSocket = ({ socketRefManager, setWsData, children }) => {
  const accessToken = useSelector((state) => state.accessToken);
  // -------------------------------------------------
  // Chat Socket Request Handler Start
  // -------------------------------------------------
  const [sendReq, setSendReq] = useState(false);
  const { socketRef, send } = useWebSocket({
    sendReq,
    setSendReq,
    url: `${TEACHER_API_ROUTE}?token=${accessToken}`,
    onMessage: (event) => {
      const data = JSON.parse(event.data);
      setWsData((prev) => ({ ...prev, ...data }));
    },
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
