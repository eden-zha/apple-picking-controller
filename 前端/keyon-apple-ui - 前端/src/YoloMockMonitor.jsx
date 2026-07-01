import {
  Activity,
  Apple,
  Camera,
  Download,
  Gauge,
  Play,
  RotateCcw,
  Square,
} from "lucide-react";

const StatTile = ({ label, value, icon: Icon }) => (
  <div className="rounded-3xl border border-white/10 bg-white/5 p-5">
    <Icon className="mb-4 h-7 w-7 text-red-300" />
    <p className="text-sm font-bold text-slate-400">{label}</p>
    <p className="mt-2 text-3xl font-black text-white">{value}</p>
  </div>
);

export default function YoloMockMonitor({
  stats,
  connectionStatus,
  onStart,
  onStop,
  onReset,
  onExport,
}) {
  const disconnected = connectionStatus !== "connected" || !stats?.running;

  return (
    <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
      <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/30">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-bold text-red-300">YOLO Mock Monitor</p>
            <h2 className="mt-1 text-3xl font-black text-white">视觉识别联调</h2>
          </div>
          <div
            className={`rounded-full px-4 py-2 text-sm font-black ${
              disconnected
                ? "bg-red-500/15 text-red-100"
                : "bg-emerald-400/10 text-emerald-300"
            }`}
          >
            {connectionStatus}
          </div>
        </div>

        <div className="grid min-h-[340px] place-items-center rounded-3xl border border-dashed border-white/15 bg-black/30 p-8 text-center">
          <div>
            <Camera className="mx-auto mb-5 h-16 w-16 text-slate-300" />
            <p className="text-2xl font-black text-white">Mock Video Placeholder</p>
            <p className="mt-3 max-w-md text-slate-400">
              当前阶段不接 USB 摄像头、不接 YOLO、不做真实视频推理。
            </p>
            {disconnected && (
              <p className="mt-5 rounded-2xl border border-red-300/30 bg-red-500/15 px-5 py-4 text-sm font-bold text-red-100">
                后端未连接或视觉模拟服务未启动
              </p>
            )}
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <button
            onClick={onStart}
            className="flex items-center justify-center gap-2 rounded-2xl bg-emerald-400 px-4 py-4 font-black text-slate-950 hover:bg-emerald-300"
          >
            <Play className="h-5 w-5" />
            start
          </button>
          <button
            onClick={onStop}
            className="flex items-center justify-center gap-2 rounded-2xl bg-red-500 px-4 py-4 font-black text-white hover:bg-red-400"
          >
            <Square className="h-5 w-5" />
            stop
          </button>
          <button
            onClick={onReset}
            className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/10 px-4 py-4 font-black text-white hover:bg-white/15"
          >
            <RotateCcw className="h-5 w-5" />
            reset
          </button>
          <button
            onClick={onExport}
            className="flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/10 px-4 py-4 font-black text-white hover:bg-white/15"
          >
            <Download className="h-5 w-5" />
            export
          </button>
        </div>
      </div>

      <div className="grid gap-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <StatTile label="初始苹果" value={stats?.initial_total ?? "--"} icon={Apple} />
          <StatTile label="当前苹果" value={stats?.current_total ?? "--"} icon={Camera} />
          <StatTile label="已采摘" value={stats?.picked_total ?? "--"} icon={Activity} />
          <StatTile label="FPS" value={stats?.fps ?? "--"} icon={Gauge} />
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/30">
          <h3 className="mb-4 text-2xl font-black text-white">状态信息</h3>
          <div className="grid gap-3">
            {[
              ["camera_status", stats?.camera_status ?? "mock"],
              ["model_status", stats?.model_status ?? "mock_running"],
              ["running", stats?.running ? "true" : "false"],
              ["red_count", stats?.red_count ?? "--"],
              ["green_count", stats?.green_count ?? "--"],
              ["updated_at", stats?.updated_at ?? "--"],
              ["message", stats?.message ?? "等待视觉模拟数据"],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex items-center justify-between gap-4 rounded-2xl bg-white/5 px-4 py-3"
              >
                <span className="text-sm font-bold text-slate-400">{label}</span>
                <span className="break-words text-right font-black text-white">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
