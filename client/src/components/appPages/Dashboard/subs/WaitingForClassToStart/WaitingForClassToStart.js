import Div from "@/baseComponents/reusableComponents/Div";
import Button from "@/baseComponents/reusableComponents/Button";

const WaitingForClassToStart = ({ setClassStarted }) => {
  return (
    <>
      <Div
        type="flex"
        hAlign="center"
        vAlign="center"
        className="height-vh-full width-per-100 bg-silver"
      >
        <Button
          btnText={"Start Class"}
          className="width-px-300"
          onClick={() => setClassStarted(true)}
        />
      </Div>
    </>
  );
};

export default WaitingForClassToStart;
