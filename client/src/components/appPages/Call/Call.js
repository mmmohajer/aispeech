import { useState, useEffect, useRef } from "react";

import Div from "@/baseComponents/reusableComponents/Div";
import ConnectionToSocket from "@/baseComponents/reusableComponents/ConnectionToSocket";

import { TRANSLATOR_API_ROUTE } from "@/constants/apiRoutes";

import NotInTheRoom from "./subs/NotInTheRoom";
import Room from "./subs/Room";
import { handleWsData } from "./utils";

const Call = () => {
  const socketRefManager = useRef();

  const [sendWsReq, setSendWsReq] = useState(false);
  const [roomId, setRoomId] = useState(0);
  const [wsData, setWsData] = useState({});

  useEffect(() => {
    handleWsData(socketRefManager, wsData);
  }, [wsData]);

  useEffect(() => {
    if (roomId > 0) {
      setSendWsReq(true);
    }
  }, [roomId]);

  return (
    <>
      <ConnectionToSocket
        socketRefManager={socketRefManager}
        setWsData={setWsData}
        sendWsReq={sendWsReq}
        wsUrl={`${TRANSLATOR_API_ROUTE}${roomId}/`}
      >
        {!wsData?.connection ? <NotInTheRoom setRoomId={setRoomId} /> : null}
        {wsData?.connection && roomId ? (
          <Room wsData={wsData} roomId={roomId} />
        ) : null}
      </ConnectionToSocket>
    </>
  );
};

export default Call;
