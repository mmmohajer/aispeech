import Div from "@/baseComponents/reusableComponents/Div";
import Typing from "@/baseComponents/reusableComponents/Typing";
import VoiceStreaming from "@/baseComponents/reusableComponents/VoiceStreaming";

import { htmlContent } from "./constants";

const Home = () => {
  return (
    <>
      <Div className="flex--gr--1 bg-green">
        <VoiceStreaming />
      </Div>
    </>
  );
};

export default Home;
