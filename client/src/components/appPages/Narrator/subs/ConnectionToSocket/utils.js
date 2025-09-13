export const handleWsData = (
  socketRefManager,
  wsData,
  setSlides,
  setSpeech,
  setShowLoader
) => {
  console.log("wsData", wsData);
  if (wsData?.connection && !handleWsData.hasStartedClass) {
    socketRefManager.current.send({ task: "start_the_class" });
    handleWsData.hasStartedClass = true;
  }
  if (wsData?.slide_alignment && wsData.slide_alignment.length > 0) {
    setSlides((prev) =>
      prev ? [...prev, wsData.slide_alignment] : [wsData.slide_alignment]
    );
  }
  if (wsData?.remove_loader) {
    setShowLoader(false);
  }
  if (wsData?.speech) {
    setSpeech(wsData.speech);
  }
};
