import Div from "@/baseComponents/reusableComponents/Div";
import Button from "@/baseComponents/reusableComponents/Button";

const NotInTheRoom = ({ setRoomId }) => {
  return (
    <>
      <Div
        type="flex"
        hAlign="center"
        vAlign="center"
        className="height-vh-full width-per-100"
      >
        <Button btnText="Join Room" onClick={() => setRoomId(12345)} />
      </Div>
    </>
  );
};

export default NotInTheRoom;
