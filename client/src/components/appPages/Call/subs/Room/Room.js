import Div from "@/baseComponents/reusableComponents/Div";

import Streaming from "./subs/Streaming";

const Room = ({ roomId }) => {
  return (
    <>
      <Streaming roomId={roomId} />
    </>
  );
};

export default Room;
