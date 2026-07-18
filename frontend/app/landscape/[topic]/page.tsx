import LandscapeView from "./LandscapeView";

export default function LandscapePage({ params }: { params: { topic: string } }) {
  const topic = decodeURIComponent(params.topic);
  return <LandscapeView topic={topic} />;
}
