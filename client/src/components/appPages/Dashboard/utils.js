export const handleWsData = (socketRefManager, wsData) => {
  console.log(wsData);
  if (wsData?.connection && !handleWsData.hasStartedClass) {
    socketRefManager.current.send({ task: "start_the_class" });
    handleWsData.hasStartedClass = true;
  }
};
