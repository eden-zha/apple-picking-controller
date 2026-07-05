import { useEffect, useState } from "react";
import {
  Apple,
  Battery,
  Package,
  Settings,
  BarChart3,
  Play,
  Square,
  Pause,
  SkipForward,
  Hand,
  AlertTriangle,
  Camera,
  Route,
  Sun,
  Wifi,
  CheckCircle2,
  ClipboardCheck,
  X,
  Bot,
  Gauge,
  Zap,
  ChevronRight,
  MapPin,
  Timer,
  Wrench,
  Volume2,
  ShieldCheck,
  Activity,
} from "lucide-react";
import {
  continuePolicyCalibration,
  getStatus,
  API_BASE_URL,
  resetTask,
  setTargetMaturity,
  startTask,
  stopTask,
  subscribeStatus,
  subscribeVision,
} from "./api";

const logoSrc = `${import.meta.env.BASE_URL}keyon-logo.png`;

const targetMaturityLabels = {
  red: "成熟果",
  yellow: "半成熟果",
};

const stateLabels = {
  IDLE: "待命",
  RUNNING: "运行中",
  DONE: "已完成",
  STOPPED: "已停止",
  ERROR: "异常",
};

const Card = ({ children, className = "" }) => (
  <div
    className={`rounded-3xl border border-white/10 bg-white/[0.06] shadow-2xl shadow-black/30 backdrop-blur ${className}`}
  >
    {children}
  </div>
);

const BigButton = ({
  children,
  onClick,
  variant = "default",
  className = "",
}) => {
  const styles = {
    default: "bg-white/10 hover:bg-white/15 border-white/10 text-white",
    red: "bg-red-500 hover:bg-red-400 border-red-300/30 text-white shadow-red-500/30",
    green:
      "bg-emerald-500 hover:bg-emerald-400 border-emerald-300/30 text-slate-950 shadow-emerald-500/30",
    dark: "bg-slate-900 hover:bg-slate-800 border-white/10 text-white",
  };

  return (
    <button
      onClick={onClick}
      className={`rounded-3xl border px-6 py-5 text-left font-bold shadow-xl transition active:scale-[0.98] ${styles[variant]} ${className}`}
    >
      {children}
    </button>
  );
};

export default function App() {
  const [page, setPage] = useState("home");
  const [status, setStatus] = useState("待命");
  const [picked] = useState(0);
  const [skipped, setSkipped] = useState(0);
  const [basket] = useState(28);
  const [mode, setMode] = useState("成熟果");
  const [area, setArea] = useState("A 区");
  const [routeMode, setRouteMode] = useState("自动路线");
  const [modal, setModal] = useState(null);
  const [currentAlert, setCurrentAlert] = useState(null);
  const [calibrationInteraction, setCalibrationInteraction] = useState(null);
  const [apiError, setApiError] = useState("");
  const [apiMessage, setApiMessage] = useState("");
  const [taskStatus, setTaskStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isLogPreviewOpen, setIsLogPreviewOpen] = useState(false);
  const [isLogPreviewPinned, setIsLogPreviewPinned] = useState(false);
  const [visionStatus, setVisionStatus] = useState({
    total: 0,
    red: 0,
    yellow: 0,
    fps: 0,
    status: "stopped",
    apple_list: [],
  });

  const normalizeLogs = (value) => {
    if (Array.isArray(value)) return value;
    if (typeof value === "string" && value.trim()) return [value];
    return [];
  };

  const applyStatus = (data) => {
    if (!data) return;
    const nextStatus = data.status || data;
    const nextTaskState = nextStatus.task_state || nextStatus.state;

    setTaskStatus(nextStatus);
    if (nextTaskState) {
      setStatus(stateLabels[nextTaskState] || nextTaskState);
    }

    if (nextStatus.target_maturity) {
      setMode(
        targetMaturityLabels[nextStatus.target_maturity] ||
          nextStatus.target_maturity
      );
    }

    if (nextStatus.logs) {
      setLogs(normalizeLogs(nextStatus.logs));
    }

    if (nextStatus.vision_status) {
      setVisionStatus(nextStatus.vision_status);
    }

    const pendingInteraction = nextStatus.policy_status?.pending_interaction;
    if (pendingInteraction?.type === "calibration_confirmation") {
      setCalibrationInteraction(pendingInteraction);
      setModal((current) => current || "calibration");
    } else {
      setCalibrationInteraction(null);
      setModal((current) => (current === "calibration" ? null : current));
    }
  };

  const refreshStatus = async () => {
    try {
      const data = await getStatus();
      applyStatus(data);
      setApiError("");
    } catch (error) {
      setApiError(error.message || "后端未连接，请先启动 FastAPI 服务");
    }
  };

  useEffect(() => {
    if (page !== "work") return undefined;

    return subscribeStatus({
      onMessage: (data) => {
        applyStatus(data);
        setApiError("");
      },
      onError: () => {
        setApiError("状态 WebSocket 未连接，请检查 robot PC 后端。");
      },
    });
  }, [page]);

  useEffect(() => {
    if (page !== "work") return undefined;

    return subscribeVision({
      onMessage: (data) => {
        setVisionStatus(data);
        setApiError("");
      },
      onError: () => {
        setApiError("视觉 WebSocket 未连接，请检查 robot PC 后端。");
      },
    });
  }, [page]);

  const startWork = async () => {
    try {
      setApiError("");
      setApiMessage("");
      const data = await startTask();
      applyStatus(data);
      setStatus("任务已启动，正在获取状态");
      setPage("work");
    } catch (error) {
      setApiError(error.message || "后端未连接，请先启动 FastAPI 服务");
    }
  };

  const togglePause = () => {
    setApiMessage("暂停/继续暂未接入后端。");
  };

  const skipTree = () => {
    setSkipped((v) => v + 1);
    setApiMessage("跳过单棵树暂未接入后端。");
  };

  const harvestOne = () => {
    setApiMessage("模拟采摘按钮暂未接入后端。");
  };

  const handleModeSelect = async (item) => {
    setMode(item);
    setApiError("");

    const targetMaturity =
      item === "成熟果" ? "red" : item === "半成熟果" ? "yellow" : null;

    if (!targetMaturity) {
      setApiMessage(
        "该成熟度暂未接入，当前仅支持成熟果和半成熟果。"
      );
      return;
    }

    try {
      const data = await setTargetMaturity(targetMaturity);
      applyStatus(data);
      setApiMessage(`已设置目标：${targetMaturityLabels[targetMaturity]}`);
    } catch (error) {
      setApiError(error.message || "后端未连接，请先启动 FastAPI 服务");
    }
  };

  const handleUnsupportedSetting = (setter, value) => {
    setter(value);
    setApiMessage("该设置暂未接入后端，仅作为界面展示。");
  };

  const handleStopTask = async () => {
    try {
      setApiError("");
      const data = await stopTask();
      applyStatus(data);
      setStatus("已停止");
      await refreshStatus();
      setModal("stop");
    } catch (error) {
      setApiError(error.message || "后端未连接，请先启动 FastAPI 服务");
    }
  };

  const handleContinueCalibration = async () => {
    try {
      setApiError("");
      const data = await continuePolicyCalibration();
      if (data?.policy_status) {
        applyStatus({ policy_status: data.policy_status });
      }
      setCalibrationInteraction(null);
      setModal(null);
      await refreshStatus();
      setApiMessage("已继续使用校准文件。");
    } catch (error) {
      setApiError(error.message || "继续校准失败，请检查后端。");
    }
  };

  const handleStopCalibration = async () => {
    setCalibrationInteraction(null);
    await handleStopTask();
  };
  const handleResetTask = async () => {
    try {
      setApiError("");
      setApiMessage("");
      const data = await resetTask();
      applyStatus(data);
      setTaskStatus(null);
      setLogs([]);
      setStatus("待命");
      setPage("home");
      setApiMessage("系统已复位。");
    } catch (error) {
      setApiError(error.message || "后端未连接，请先启动 FastAPI 服务");
    }
  };

  const navItems = [
    { id: "home", label: "今日任务", icon: Apple },
    { id: "settings", label: "采摘设置", icon: Settings },
    { id: "work", label: "工作中", icon: Bot },
    { id: "alerts", label: "异常处理", icon: AlertTriangle },
    { id: "report", label: "今日成果", icon: BarChart3 },
  ];

  const alerts = [
    {
      title: "前方被树叶挡住了",
      desc: "机器人看不清苹果，建议换个角度再试。",
      icon: Camera,
      level: "轻微",
    },
    {
      title: "果筐快满了",
      desc: "请准备更换果筐，避免苹果堆压。",
      icon: Package,
      level: "提醒",
    },
    {
      title: "机械臂碰到树枝",
      desc: "机器人已停止动作，需要回到安全姿态。",
      icon: Wrench,
      level: "注意",
    },
    {
      title: "摄像头需要擦拭",
      desc: "画面可能有灰尘或水雾，建议人工检查。",
      icon: AlertTriangle,
      level: "提醒",
    },
  ];

  const LogoPlate = () => (
    <div className="relative flex items-center gap-5">
      <div className="relative overflow-hidden rounded-[2rem] border border-white/15 bg-gradient-to-br from-white/16 via-white/7 to-white/[0.03] p-[1px] shadow-2xl shadow-red-950/40">
        <div className="absolute left-0 top-0 h-full w-1/2 bg-red-500/14 blur-2xl" />

        <div className="relative flex h-[96px] w-[245px] items-center rounded-[1.9rem] border border-white/10 bg-slate-950/78 px-4">
          <div className="relative flex h-[72px] w-full items-center justify-center overflow-hidden rounded-2xl border border-white/20 bg-white px-4 shadow-inner shadow-black/20">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.9),rgba(255,255,255,1)_55%,rgba(241,245,249,1))]" />

            <img
              src={logoSrc}
              alt="颗沿 Keyon Logo"
              className="relative w-full object-contain"
              style={{
                transform: "scale(0.51)",
                transformOrigin: "center center",
              }}
            />
          </div>
        </div>
      </div>

      <div className="hidden xl:block">
        <div className="flex items-center gap-2 text-sm font-bold text-red-200">
          <Activity className="h-4 w-4" />
          Orchard Robot Interface
        </div>
        <h1 className="mt-1 text-3xl font-black tracking-tight text-white">
          颗沿 Keyon 中控
        </h1>
        <p className="text-sm text-slate-400">
          采苹果机器人 · 田间平板控制端
        </p>
      </div>
    </div>
  );

  const Header = () => (
    <div className="flex items-center justify-between gap-4">
      <LogoPlate />

      <div className="flex flex-wrap items-center justify-end gap-3">
        <div
          className="relative hidden lg:block"
          onMouseEnter={() => setIsLogPreviewOpen(true)}
          onMouseLeave={() => {
            if (!isLogPreviewPinned) setIsLogPreviewOpen(false);
          }}
        >
          <button
            type="button"
            onClick={() => {
              const nextPinned = !isLogPreviewPinned;
              setIsLogPreviewPinned(nextPinned);
              setIsLogPreviewOpen(nextPinned || !isLogPreviewOpen);
            }}
            className={`flex max-w-sm items-center gap-3 rounded-2xl border px-4 py-3 text-left text-xs text-slate-300 transition ${
              isLogPreviewPinned
                ? "border-emerald-300/30 bg-emerald-400/10"
                : "border-white/10 bg-white/5 hover:bg-white/10"
            }`}
          >
            <ClipboardCheck className="h-4 w-4 shrink-0 text-emerald-300" />
            <div className="min-w-0">
              <p className="font-bold text-slate-100">运行日志</p>
              <p className="truncate text-slate-400">
                {isLogPreviewPinned ? "已固定，点击收起" : "悬停预览，点击固定"}
              </p>
            </div>
          </button>

          {isLogPreviewOpen && (
            <div className="absolute right-0 top-[calc(100%+0.75rem)] z-40 w-96 rounded-2xl border border-white/10 bg-slate-950/95 p-4 text-sm shadow-2xl shadow-black/50 backdrop-blur">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="font-black text-white">最近运行日志</p>
                <span className="rounded-full bg-white/10 px-2 py-1 text-xs font-bold text-slate-300">
                  {isLogPreviewPinned ? "已固定" : "预览"}
                </span>
              </div>

              <div className="max-h-56 overflow-y-auto rounded-xl bg-black/25 p-3">
                {recentLogs.length > 0 ? (
                  recentLogs.map((item, index) => (
                    <p
                      key={`${item}-${index}`}
                      className="border-b border-white/10 py-2 text-xs leading-relaxed text-slate-300 last:border-b-0"
                    >
                      {item}
                    </p>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">暂无日志。</p>
                )}
              </div>
            </div>
          )}
        </div>
        <div className="hidden items-center gap-2 rounded-2xl border border-emerald-300/20 bg-emerald-400/10 px-4 py-3 text-sm font-bold text-emerald-300 md:flex">
          <ShieldCheck className="h-4 w-4" />
          设备在线
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
          14:30
        </div>
      </div>
    </div>
  );

  const Nav = () => (
    <Card className="p-3">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = page === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`flex items-center justify-center gap-2 rounded-2xl px-4 py-4 text-sm font-bold transition ${
                active
                  ? "bg-red-500 text-white shadow-lg shadow-red-500/25"
                  : "bg-white/5 text-slate-300 hover:bg-white/10"
              }`}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </button>
          );
        })}
      </div>
    </Card>
  );

  const NoticeBar = () => {
    if (!apiError && !apiMessage) return null;

    return (
      <div
        className={`rounded-2xl border px-5 py-4 text-sm font-bold ${
          apiError
            ? "border-red-300/30 bg-red-500/15 text-red-100"
            : "border-emerald-300/30 bg-emerald-400/10 text-emerald-100"
        }`}
      >
        {apiError || apiMessage}
      </div>
    );
  };

  const progressValue = Number.isFinite(taskStatus?.progress)
    ? Math.min(Math.max(taskStatus.progress, 0), 100)
    : Math.min(25 + picked, 100);

  const backendState = taskStatus?.task_state || taskStatus?.state;

  const backendStateText = backendState
    ? stateLabels[backendState] || backendState
    : "未连接";

  const backendTargetText = taskStatus?.target_maturity
    ? targetMaturityLabels[taskStatus.target_maturity] || taskStatus.target_maturity
    : "未设置";

  const recentLogs = logs.slice(-10).reverse();

  const HomePage = () => (
    <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
      <Card className="overflow-hidden p-8">
        <div className="mb-8 flex items-start justify-between gap-6">
          <div>
            <p className="mb-2 text-sm font-bold text-red-300">今日任务</p>
            <h2 className="text-5xl font-black text-white">A 区苹果采摘</h2>
            <p className="mt-4 max-w-xl text-lg text-slate-300">
              当前推荐目标：成熟果。机器人将自动沿果树行进，按成熟度策略识别并采摘苹果。
            </p>
          </div>

          <div className="rounded-full bg-emerald-400/10 px-5 py-3 text-sm font-bold text-emerald-300">
            准备就绪
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <BigButton
            onClick={startWork}
            variant="green"
            className="flex items-center justify-between text-2xl"
          >
            <span className="flex items-center gap-4">
              <Play className="h-9 w-9" />
              开始采摘
            </span>
            <ChevronRight className="h-7 w-7" />
          </BigButton>

          <BigButton
            onClick={handleStopTask}
            variant="red"
            className="flex items-center justify-between text-2xl"
          >
            <span className="flex items-center gap-4">
              <Square className="h-9 w-9" />
              紧急停止
            </span>
            <AlertTriangle className="h-7 w-7" />
          </BigButton>
        </div>
      </Card>

      <div className="grid gap-5">
        <Card className="p-6">
          <div className="mb-5 flex items-center gap-3">
            <Sun className="h-6 w-6 text-yellow-300" />
            <h3 className="text-xl font-black text-white">田间状态</h3>
          </div>

          <div className="grid gap-3">
            {[
              ["天气", "晴 26℃", Sun],
              ["电量", "88%", Battery],
              ["信号", "稳定", Wifi],
              ["果筐", `${basket}%`, Package],
            ].map(([name, value, Icon]) => (
              <div
                key={name}
                className="flex items-center justify-between rounded-2xl bg-white/5 p-4"
              >
                <span className="flex items-center gap-3 text-slate-300">
                  <Icon className="h-5 w-5 text-slate-400" />
                  {name}
                </span>
                <span className="text-lg font-black text-white">{value}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <div className="mb-4 flex items-center gap-3">
            <Volume2 className="h-6 w-6 text-emerald-300" />
            <h3 className="text-xl font-black text-white">语音提示</h3>
          </div>
          <p className="text-slate-300">
            “设备已准备好。请确认果筐为空，周围无人靠近机械臂。”
          </p>
        </Card>
      </div>
    </div>
  );

  const SettingsPage = () => (
    <div className="grid gap-5">
      <Card className="p-7">
        <h2 className="mb-6 text-3xl font-black text-white">采摘设置</h2>

        <div className="grid gap-6 lg:grid-cols-3">
          <div>
            <p className="mb-3 font-bold text-slate-300">成熟度选择</p>
            <div className="grid gap-3">
              {["成熟果", "半成熟果"].map(
                (item) => (
                  <button
                    key={item}
                    onClick={() => handleModeSelect(item)}
                    className={`flex min-h-[104px] items-center rounded-2xl border p-5 text-left text-lg font-black transition ${
                      mode === item
                        ? "border-red-300 bg-red-500 text-white"
                        : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                    }`}
                  >
                    {item}
                  </button>
                )
              )}
            </div>
          </div>

          <div>
            <p className="mb-3 font-bold text-slate-300">区域选择</p>
            <div className="grid gap-3">
              {["A 区", "B 区", "C 区"].map((item) => (
                <button
                  key={item}
                  onClick={() => handleUnsupportedSetting(setArea, item)}
                  className={`rounded-2xl border p-5 text-left text-lg font-black transition ${
                    area === item
                      ? "border-emerald-300 bg-emerald-400 text-slate-950"
                      : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                  }`}
                >
                  <MapPin className="mb-2 h-6 w-6" />
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-3 font-bold text-slate-300">路线模式</p>
            <div className="grid gap-3">
              {["自动路线", "沿行采摘", "返回起点"].map((item) => (
                <button
                  key={item}
                  onClick={() => handleUnsupportedSetting(setRouteMode, item)}
                  className={`rounded-2xl border p-5 text-left text-lg font-black transition ${
                    routeMode === item
                      ? "border-sky-300 bg-sky-400 text-slate-950"
                      : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
                  }`}
                >
                  <Route className="mb-2 h-6 w-6" />
                  {item}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );

  const WorkPage = () => (
    <div className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
      <Card className="p-8">
        <p className="mb-2 text-sm font-bold text-emerald-300">当前状态</p>
        <h2 className="mb-6 text-5xl font-black text-white">{status}</h2>

        <div className="mb-8 h-5 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-red-400 transition-all"
            style={{ width: `${progressValue}%` }}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <BigButton onClick={togglePause} variant="dark" className="text-xl">
            <Pause className="mb-3 h-8 w-8 text-yellow-300" />
            {status === "已暂停" ? "继续" : "暂停"}
          </BigButton>

          <BigButton onClick={skipTree} variant="dark" className="text-xl">
            <SkipForward className="mb-3 h-8 w-8 text-sky-300" />
            跳过这棵
          </BigButton>

          <BigButton
            onClick={() => setModal("control")}
            variant="red"
            className="text-xl"
          >
            <Hand className="mb-3 h-8 w-8 text-white" />
            人工接管
          </BigButton>
        </div>

        <button
          onClick={harvestOne}
          className="mt-4 w-full rounded-3xl border border-emerald-300/30 bg-emerald-400/10 p-5 text-lg font-black text-emerald-300 transition hover:bg-emerald-400/15"
        >
          模拟采摘 3 个苹果
        </button>

        <button
          onClick={handleStopTask}
          className="mt-4 w-full rounded-3xl border border-red-300/30 bg-red-500/15 p-5 text-lg font-black text-red-100 transition hover:bg-red-500/20"
        >
          紧急停止
        </button>
      </Card>

      <div className="grid gap-5">
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {[
            ["融合状态", backendStateText, Activity],
            ["任务进度", `${progressValue}%`, Gauge],
            ["目标模式", backendTargetText, Apple],
            ["机器人状态", taskStatus?.robot_status?.running ? "运行中" : "未运行", Timer],
          ].map(([name, value, Icon]) => (
            <Card key={name} className="p-4">
              <Icon className="mb-3 h-6 w-6 text-red-300" />
              <p className="text-sm font-bold text-slate-400">{name}</p>
              <p className="mt-1 break-words text-xl font-black text-white">
                {value}
              </p>
            </Card>
          ))}
        </div>

        <Card className="p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-emerald-300">YOLO WebSocket</p>
              <h3 className="text-2xl font-black text-white">实时画面果数</h3>
            </div>
            <div className={`rounded-full px-3 py-1 text-sm font-bold ${
              visionStatus.status === "running"
                ? "bg-emerald-400/10 text-emerald-300"
                : visionStatus.status === "fallback"
                  ? "bg-yellow-300/10 text-yellow-200"
                  : "bg-white/10 text-slate-300"
            }`}>
              {visionStatus.status}
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {[
              ["苹果总数", visionStatus.total, Apple, "text-white"],
              ["红苹果", visionStatus.red, Apple, "text-red-300"],
              ["黄苹果", visionStatus.yellow, Apple, "text-yellow-200"],
            ].map(([name, value, Icon, color]) => (
              <div key={name} className="rounded-2xl border border-white/10 bg-black/20 p-5">
                <Icon className={`mb-4 h-7 w-7 ${color}`} />
                <p className="text-sm font-bold text-slate-400">{name}</p>
                <p className="mt-1 text-5xl font-black text-white">{value}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );

  const AlertsPage = () => (
    <div className="grid gap-5">
      <Card className="p-7">
        <h2 className="mb-2 text-3xl font-black text-white">异常处理</h2>

        <div className="grid gap-4 md:grid-cols-2">
          {alerts.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.title}
                onClick={() => {
                  setCurrentAlert(item);
                  setModal("alert");
                }}
                className="rounded-3xl border border-white/10 bg-white/5 p-6 text-left transition hover:bg-white/10"
              >
                <div className="mb-5 flex items-center justify-between">
                  <Icon className="h-9 w-9 text-yellow-300" />
                  <span className="rounded-full bg-yellow-300/10 px-3 py-1 text-sm font-bold text-yellow-200">
                    {item.level}
                  </span>
                </div>
                <h3 className="mb-2 text-2xl font-black text-white">
                  {item.title}
                </h3>
                <p className="text-slate-400">{item.desc}</p>
              </button>
            );
          })}
        </div>
      </Card>
    </div>
  );

  const ReportPage = () => (
    <div className="grid gap-5 lg:grid-cols-[1fr_0.8fr]">
      <Card className="p-8">
        <h2 className="mb-6 text-4xl font-black text-white">今日成果</h2>

        <div className="grid gap-5 md:grid-cols-2">
          {[
            ["采摘总量", `${picked} 个`, Apple],
            ["精品果", `${Math.round(picked * 0.72)} 个`, CheckCircle2],
            ["跳过数量", `${skipped} 棵`, SkipForward],
            ["工作时长", "2 小时 18 分", Timer],
          ].map(([name, value, Icon]) => (
            <div key={name} className="rounded-3xl bg-white/5 p-6">
              <Icon className="mb-4 h-8 w-8 text-emerald-300" />
              <p className="text-sm font-bold text-slate-400">{name}</p>
              <p className="mt-2 text-4xl font-black text-white">{value}</p>
            </div>
          ))}
        </div>

        <button
          onClick={() => setModal("report")}
          className="mt-6 flex w-full items-center justify-between rounded-3xl bg-red-500 px-7 py-6 text-left text-2xl font-black text-white shadow-xl shadow-red-500/25 transition hover:bg-red-400"
        >
          <span className="flex items-center gap-4">
            <ClipboardCheck className="h-9 w-9" />
            生成今日报告
          </span>
          <ChevronRight />
        </button>
      </Card>

      <Card className="p-8">
        <Gauge className="mb-5 h-10 w-10 text-sky-300" />
        <h3 className="text-2xl font-black text-white">节省人工估算</h3>
        <p className="mt-4 text-slate-300">
          当前工作量约等于 1.6
          名熟练工人的半日采摘量。数据为 demo 模拟值，用于比赛展示。
        </p>
      </Card>
    </div>
  );

  const Modal = () => {
    if (!modal) return null;

    let content = null;

    if (modal === "stop") {
      content = (
        <>
          <AlertTriangle className="mx-auto mb-5 h-14 w-14 text-red-400" />
          <h3 className="text-center text-3xl font-black text-white">
            已触发紧急停止
          </h3>
          <p className="mt-4 text-center text-slate-300">
            机械臂将停止动作，小车保持原地等待人工确认。
          </p>
        </>
      );
    }

    if (modal === "control") {
      content = (
        <>
          <Hand className="mx-auto mb-5 h-14 w-14 text-yellow-300" />
          <h3 className="text-center text-3xl font-black text-white">
            人工接管提示
          </h3>
          <p className="mt-4 text-center text-slate-300">
            请确认机械臂周围无人，再接管机器人方向和采摘动作。
          </p>
        </>
      );
    }

    if (modal === "calibration") {
      content = (
        <>
          <AlertTriangle className="mx-auto mb-5 h-14 w-14 text-yellow-300" />
          <h3 className="text-center text-3xl font-black text-white">
            机械臂校准确认
          </h3>
          <p className="mt-4 text-center text-slate-300">
            LeRobot 检测到电机当前校准值和校准文件不一致。请选择继续使用已提供的校准文件，或停止当前任务。
          </p>
          {calibrationInteraction?.excerpt && (
            <p className="mt-4 rounded-2xl bg-black/25 p-4 text-xs leading-relaxed text-slate-400">
              {calibrationInteraction.excerpt}
            </p>
          )}
          <div className="mt-6 grid grid-cols-2 gap-3">
            <button
              onClick={handleContinueCalibration}
              className="rounded-2xl bg-emerald-500 p-4 font-bold text-slate-950 hover:bg-emerald-400"
            >
              继续
            </button>
            <button
              onClick={handleStopCalibration}
              className="rounded-2xl bg-red-500 p-4 font-bold text-white hover:bg-red-400"
            >
              停止工作
            </button>
          </div>
        </>
      );
    }
    if (modal === "alert") {
      content = (
        <>
          <AlertTriangle className="mx-auto mb-5 h-14 w-14 text-yellow-300" />
          <h3 className="text-center text-3xl font-black text-white">
            {currentAlert?.title}
          </h3>
          <p className="mt-4 text-center text-slate-300">
            {currentAlert?.desc}
          </p>

          <div className="mt-6 grid grid-cols-2 gap-3">
            {["再试一次", "跳过", "回安全姿态", "呼叫人工"].map((item) => (
              <button
                key={item}
                onClick={() => setModal(null)}
                className="rounded-2xl bg-white/10 p-4 font-bold text-white hover:bg-white/15"
              >
                {item}
              </button>
            ))}
          </div>
        </>
      );
    }

    if (modal === "report") {
      content = (
        <>
          <ClipboardCheck className="mx-auto mb-5 h-14 w-14 text-emerald-300" />
          <h3 className="text-center text-3xl font-black text-white">
            今日报告已生成
          </h3>
          <p className="mt-4 text-center text-slate-300">
            今日完成 {area} 采摘，采摘 {picked} 个苹果，精品果约{" "}
            {Math.round(picked * 0.72)} 个，跳过 {skipped} 棵树。
          </p>
        </>
      );
    }

    return (
      <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-6 backdrop-blur">
        <div className="relative w-full max-w-lg rounded-3xl border border-white/10 bg-slate-950 p-8 shadow-2xl">
          <button
            onClick={() => setModal(null)}
            className="absolute right-5 top-5 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"
          >
            <X className="h-5 w-5" />
          </button>

          {content}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,#7f1d1d_0,#020617_34%,#020617_100%)] p-5 text-white md:p-8">
      <div className="mx-auto max-w-7xl space-y-5">
        <Header />
        <Nav />
        <NoticeBar />

        <div className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-5 shadow-2xl shadow-black/40 md:p-7">
          {page === "home" && <HomePage />}
          {page === "settings" && <SettingsPage />}
          {page === "work" && <WorkPage />}
          {page === "alerts" && <AlertsPage />}
          {page === "report" && <ReportPage />}
        </div>

        <Card className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-center gap-3 text-slate-300">
            <Bot className="h-5 w-5 text-emerald-300" />
            当前配置：{area} · {mode} · {routeMode} · robot PC 后端
          </div>

          <div className="flex items-center gap-3 text-slate-300">
            <Zap className="h-5 w-5 text-yellow-300" />
            后端：{API_BASE_URL.replace(/^https?:\/\//, "")}
          </div>

          <button
            onClick={handleResetTask}
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-slate-200 transition hover:bg-white/10"
          >
            复位
          </button>
        </Card>
      </div>

      <Modal />
    </div>
  );
}
