export const handleMessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received data from WebSocket:", data);
  //   console.log("Received data from WebSocket:", data);
  if (data?.text) {
    console.log(data.text);
  }
  if (data?.["Google STT"]) {
    console.log("Google STT:", data["Google STT"]);
  }
  if (data?.["OpenAI STT"]) {
    console.log("OpenAI STT:", data["OpenAI STT"]);
  }
  //   if (data.type === "audio") {
  //     const chunkId = data.chunk_id;
  //     const base64Audio = data.voice_chunk;
  //     const binary = Uint8Array.from(atob(base64Audio), (c) => c.charCodeAt(0));
  //     const audioBlob = new Blob([binary], { type: "audio/webm" });
  //     const audioUrl = URL.createObjectURL(audioBlob);
  //     const audio = new Audio(audioUrl);
  //     audio.play();
  //   }
};
