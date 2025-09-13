import { useState, useEffect } from "react";

import Div from "@/baseComponents/reusableComponents/Div";
import BaseConnectionToSocket from "@/baseComponents/reusableComponents/ConnectionToSocket";
import Button from "@/baseComponents/reusableComponents/Button";

import { TEACHER_API_ROUTE } from "@/constants/apiRoutes";

import { handleWsData } from "./utils";

const ConnectionToSocket = ({
  socketRefManager,
  wsData,
  setWsData,
  sendWsReq,
  setSendWsReq,
  setSlides,
  setSpeech,
  setShowLoader,
  roomId,
}) => {
  useEffect(() => {
    handleWsData(socketRefManager, wsData, setSlides, setSpeech, setShowLoader);
  }, [wsData]);

  return (
    <>
      <BaseConnectionToSocket
        socketRefManager={socketRefManager}
        setWsData={setWsData}
        sendWsReq={sendWsReq}
        wsUrl={`${TEACHER_API_ROUTE}${roomId}/`}
      >
        <Div>
          {!wsData?.connection ? (
            <Div
              type="flex"
              hAlign="center"
              vAlign="center"
              className="height-vh-full width-per-100"
            >
              <Button
                btnText="Join Classroom"
                onClick={() => setSendWsReq(true)}
              />
            </Div>
          ) : null}
        </Div>
      </BaseConnectionToSocket>
    </>
  );
};

export default ConnectionToSocket;
