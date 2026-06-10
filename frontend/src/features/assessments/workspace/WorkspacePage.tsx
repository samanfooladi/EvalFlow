import { useParams } from "react-router-dom";

export function WorkspacePage() {
  const { id } = useParams();
  return (
    <div className="p-8 text-ink-500">
      میز کار ارزیابی #{id} — در میلستون بعدی تکمیل می‌شود.
    </div>
  );
}
