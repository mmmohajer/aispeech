import Div from "@/baseComponents/reusableComponents/Div";
import Typing from "@/baseComponents/reusableComponents/Typing";

import { htmlContent } from "./constants";

const Home = () => {
  return (
    <>
      <Div className="flex--gr--1 bg-green">
        <Typing htmlContent={htmlContent} speed={25} />
      </Div>
    </>
  );
};

export default Home;
