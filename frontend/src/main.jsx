import React from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowLeft, BookOpen, Bot, Check, CheckCircle2, ChevronDown, CircleDollarSign, ExternalLink, FileText, FolderCog, FolderOpen, LoaderCircle, Moon, Play, RotateCcw, ScrollText, Square, Sun, X } from "lucide-react";

import { loadDashboardData, openWorkDir, openWorkspacePath, resetActivity, resetMetrics, selectWorkDir, startOrchestrator, stopOrchestrator, updateOperationMode, updateWorkDir } from "./api";
import "./styles.css";

function App() {
  const [data, setData] = React.useState(null);
  const [toast, setToast] = React.useState(null);
  const [updatedAt, setUpdatedAt] = React.useState("");
  const [workDirDraft, setWorkDirDraft] = React.useState("");
  const [modeDraft, setModeDraft] = React.useState("spec-gate");
  const [modeMenuOpen, setModeMenuOpen] = React.useState(false);
  const [view, setView] = React.useState("dashboard");
  const [theme, setTheme] = React.useState(() => {
    const stored = window.localStorage.getItem("specgate-theme");
    if (stored) {
      return stored;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  const refresh = React.useCallback(async () => {
    try {
      const nextData = await loadDashboardData();
      setData(nextData);
      setUpdatedAt(new Date().toLocaleTimeString());
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to load dashboard data", "error");
    }
  }, []);

  React.useEffect(() => {
    refresh();
    const interval = data?.runStatus?.status === "running" || data?.runStatus?.status === "stopping" ? 1500 : 5000;
    const timer = window.setInterval(refresh, interval);
    return () => window.clearInterval(timer);
  }, [refresh, data?.runStatus?.status]);

  React.useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("specgate-theme", theme);
  }, [theme]);

  React.useEffect(() => {
    if (data?.config?.work_dir) {
      setWorkDirDraft(data.config.work_dir);
    }
  }, [data?.config?.work_dir]);

  React.useEffect(() => {
    if (data?.config?.operation_mode) {
      setModeDraft(data.config.operation_mode);
    }
  }, [data?.config?.operation_mode]);

  const toggleTheme = () => {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  };

  const showToast = React.useCallback((message, type = "success") => {
    setToast({ message, type });
  }, []);

  React.useEffect(() => {
    if (!toast) {
      return undefined;
    }

    const timer = window.setTimeout(() => setToast(null), toast.type === "error" ? 7000 : 4200);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const runFromDashboard = async () => {
    try {
      const result = await startOrchestrator();
      showToast(result.message);
      await refresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to start orchestrator", "error");
    }
  };

  const resetUsage = async () => {
    try {
      await resetMetrics();
      showToast("Metrics and usage reset.");
      await refresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to reset metrics", "error");
    }
  };

  const resetActivityLog = async () => {
    try {
      await resetActivity();
      showToast("Activity timeline reset.");
      await refresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to reset activity", "error");
    }
  };

  const stopRun = async () => {
    try {
      const result = await stopOrchestrator();
      showToast(result.message);
      await refresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to stop orchestrator", "error");
    }
  };

  const saveWorkDir = async (event) => {
    event.preventDefault();
    try {
      await updateWorkDir(workDirDraft);
      showToast(`Working directory set to ${workDirDraft}`);
      await refresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to update working directory", "error");
    }
  };

  const saveOperationMode = async (nextMode) => {
    setModeDraft(nextMode);
    setModeMenuOpen(false);
    try {
      await updateOperationMode(nextMode);
      showToast(`Operation mode set to ${modeLabel(nextMode)}.`);
      await refresh();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to update operation mode", "error");
    }
  };

  const browseWorkDir = async () => {
    try {
      const result = await selectWorkDir();
      if (result.selected) {
        showToast(`Working directory set to ${result.work_dir}`);
        setWorkDirDraft(result.work_dir);
        await refresh();
      }
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to choose working directory", "error");
    }
  };

  const openCurrentWorkDir = async () => {
    try {
      await openWorkDir();
      showToast("Working directory opened.");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to open working directory", "error");
    }
  };

  const openActivityFile = async (filepath, reveal = false) => {
    try {
      await openWorkspacePath(filepath, reveal);
      showToast(reveal ? "Containing folder opened." : "File opened.");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Unable to open file", "error");
    }
  };

  const status = data?.status ?? {};
  const tasks = data?.tasks ?? [];
  const journal = data?.journal ?? {};
  const graphState = data?.graphState ?? {};
  const runStatus = data?.runStatus ?? {};
  const agents = data?.agents ?? [];
  const help = data?.help?.content ?? "";
  const counts = status.task_counts ?? {};
  const completed = counts.completed ?? 0;
  const failed = counts.failed ?? 0;
  const pending = counts.pending ?? 0;
  const inProgress = counts.in_progress ?? 0;
  const total = completed + failed + pending + inProgress;
  const costRatio = Math.round((status.budget_used_ratio ?? 0) * 100);
  const isRunning = runStatus.status === "running" || runStatus.status === "stopping";
  const runStateLabel = formatRunState(runStatus.status);

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brandBlock">
          <p className="eyebrow">Spec-Gate</p>
          <h1>{status.project_name ?? "Dashboard"}</h1>
        </div>
        <div className="statusStrip">
          <span className={`runStatusPill ${runStatus.status ?? "idle"}`}>
            {isRunning ? <LoaderCircle className="spin" size={15} /> : <span className="statusLight" />}
            {runStateLabel}
          </span>
          <button className={`runButton ${isRunning ? "busy" : ""}`} type="button" onClick={runFromDashboard} disabled={isRunning}>
            {isRunning ? <LoaderCircle className="spin" size={16} /> : <Play size={16} />}
            {isRunning ? "Running" : "Run"}
          </button>
          <button className="resetButton" type="button" onClick={stopRun}>
            <Square size={15} />
            Stop
          </button>
          <button className="resetButton" type="button" onClick={resetUsage}>
            <RotateCcw size={16} />
            Reset
          </button>
          <button className="resetButton" type="button" onClick={() => setView((current) => current === "help" ? "dashboard" : "help")}>
            <BookOpen size={16} />
            Help
          </button>
          <button className="iconButton" type="button" onClick={toggleTheme} aria-label="Toggle dark mode">
            {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
          </button>
        </div>
      </header>

      {toast ? <Snackbar toast={toast} onClose={() => setToast(null)} /> : null}

      {view === "help" ? (
        <HelpView markdown={help} onBack={() => setView("dashboard")} />
      ) : (
        <>
          <section className={`runBanner panel ${isRunning ? "active" : ""}`}>
            <div>
              <span className="runBannerLabel">{runStateLabel}</span>
              <strong>{runStatus.current_step || "Waiting for dashboard action"}</strong>
              <p>{runStatus.last_error || runtimeHint(runStatus.status, graphState.next_node)}</p>
            </div>
            {isRunning ? <LoaderCircle className="spin" size={20} /> : <span className="statusLight" />}
          </section>

          <section className="metrics" aria-label="Runtime metrics">
            <Metric icon={<CheckCircle2 size={18} />} label="Tasks" value={`${completed} / ${total}`} detail={`${pending} pending, ${failed} failed`} />
            <Metric
              icon={<CircleDollarSign size={18} />}
              label="Cost"
              value={`$${Number(status.total_cost ?? 0).toFixed(4)}`}
              detail={`Budget $${Number(status.budget_limit_usd ?? 0).toFixed(2)}`}
            >
              <div className="gauge">
                <span style={{ width: `${costRatio}%` }} />
              </div>
            </Metric>
            <Metric icon={<Activity size={18} />} label="Tokens" value={Number(status.total_tokens ?? 0).toLocaleString()} detail="from model usage metadata" />
            <Metric
              icon={<FolderCog size={18} />}
              label="Active Task"
              value={status.active_task?.name ?? "None"}
              detail={status.active_task?.description ?? "Waiting for work"}
            />
          </section>

          <section className="controlPanel panel">
            <div>
              <h2><FolderCog size={17} /> Run Settings</h2>
              <p className="helper">AI-created files are restricted to this folder. Mode controls how tests gate completion.</p>
            </div>
            <form className="workdirForm" onSubmit={saveWorkDir}>
              <ModePicker
                value={modeDraft}
                open={modeMenuOpen}
                disabled={isRunning}
                onToggle={() => setModeMenuOpen((current) => !current)}
                onChange={saveOperationMode}
              />
              <input value={workDirDraft} onChange={(event) => setWorkDirDraft(event.target.value)} aria-label="AI working directory" />
              <button className="resetButton" type="button" onClick={openCurrentWorkDir}>
                <ExternalLink size={16} />
                Open
              </button>
              <button className="resetButton" type="button" onClick={browseWorkDir}>
                <FolderOpen size={16} />
                Browse
              </button>
              <button className="runButton" type="submit">
                <Check size={16} />
                Save
              </button>
            </form>
          </section>

          <section className="workspace">
            <Panel title="Tasks" aside={updatedAt || "not loaded"}>
              <TaskList tasks={tasks} />
            </Panel>

            <Panel
              title="Activity"
              icon={<ScrollText size={17} />}
              action={(
                <button className="panelActionButton" type="button" onClick={resetActivityLog}>
                  <RotateCcw size={14} />
                  Reset
                </button>
              )}
            >
              <ActivityList
                events={journal.events ?? []}
                artifacts={journal.artifacts ?? []}
                fallback={journal.journal_tail || journal.summary_tail}
                onOpenFile={openActivityFile}
              />
            </Panel>
          </section>

          <Panel title="Agents" icon={<Bot size={17} />} aside={graphState.available ? "checkpoint available" : "checkpoint unavailable"}>
            <AgentList agents={agents} activeNode={graphState.next_node} />
          </Panel>
        </>
      )}
    </main>
  );
}

function Metric({ icon, label, value, detail, children }) {
  return (
    <article className="metric">
      <div className="metricLabel">
        {icon}
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
      {children}
    </article>
  );
}

function Snackbar({ toast, onClose }) {
  return (
    <div className={`snackbar ${toast.type}`} role="status" aria-live="polite">
      <span>{toast.message}</span>
      <button type="button" onClick={onClose} aria-label="Close message">
        <X size={16} />
      </button>
    </div>
  );
}

function Panel({ title, aside, icon, action, children }) {
  return (
    <section className="panel">
      <div className="panelHead">
        <h2>{icon}{title}</h2>
        <div className="panelHeadActions">
          {aside ? <span className="timestamp">{aside}</span> : null}
          {action}
        </div>
      </div>
      {children}
    </section>
  );
}

function TaskList({ tasks }) {
  if (!tasks.length) {
    return <p className="empty">No tasks found in SPEC.md.</p>;
  }

  return (
    <div className="taskList">
      {tasks.map((task) => (
        <article className={`task ${task.status}`} key={task.id}>
          <span className="check" aria-hidden="true">{task.status === "completed" ? <Check size={13} /> : null}</span>
          <div>
            <strong>{task.name}</strong>
            <p>{task.description}</p>
          </div>
          <span className="tag">{task.status}</span>
        </article>
      ))}
    </div>
  );
}

function ModePicker({ value, open, disabled, onToggle, onChange }) {
  const selected = MODE_OPTIONS.find((mode) => mode.value === value) ?? MODE_OPTIONS[0];

  return (
    <div className="modePicker">
      <span className="modeLabel">Mode</span>
      <button
        className="modeTrigger"
        type="button"
        onClick={onToggle}
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="listbox"
        title={selected.description}
      >
        <span>
          <strong>{selected.label}</strong>
          <small>{selected.short}</small>
        </span>
        <ChevronDown size={15} />
      </button>
      {open && !disabled ? (
        <div className="modeMenu" role="listbox">
          {MODE_OPTIONS.map((mode) => (
            <button
              className={mode.value === value ? "selected" : ""}
              type="button"
              role="option"
              aria-selected={mode.value === value}
              onClick={() => onChange(mode.value)}
              title={mode.description}
              key={mode.value}
            >
              <span>
                <strong>{mode.label}</strong>
                <small>{mode.description}</small>
              </span>
              {mode.value === value ? <Check size={14} /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ActivityList({ events, artifacts, fallback, onOpenFile }) {
  if (!events.length) {
    return (
      <div className={`emptyState ${fallback ? "waiting" : ""}`}>
        {fallback ? <LoaderCircle className="spin" size={22} /> : <ScrollText size={22} />}
        <strong>No activity yet</strong>
        <p>{fallback ? "Journal entries will be converted into timeline events after the next run." : "Run a task to populate the activity timeline."}</p>
      </div>
    );
  }

  const timelineEvents = [...events].reverse();

  return (
    <>
      {artifacts.length ? (
        <div className="artifactShelf" aria-label="Changed files">
          {artifacts.map((artifact) => (
            <article className="artifactItem" key={artifact.file}>
              <FileText size={15} />
              <div>
                <strong>{artifact.file}</strong>
                <span>{artifact.action}</span>
              </div>
              <button type="button" onClick={() => onOpenFile(artifact.file)}>
                Open
              </button>
              <button type="button" onClick={() => onOpenFile(artifact.file, true)}>
                Folder
              </button>
            </article>
          ))}
        </div>
      ) : null}

      <div className="activityList">
        {timelineEvents.map((event, index) => (
          <article className={`activityItem ${event.type} ${index === 0 ? "current" : "past"}`} key={`${event.title}-${event.detail}-${index}`}>
            <span className="activityDot" />
            <div>
              <div className="activityItemHead">
                <strong>{event.title}</strong>
                {index === 0 ? <span className="currentBadge">Current</span> : null}
              </div>
              <p>{event.detail}</p>
              {event.file ? (
                <div className="activityLinks">
                  <button type="button" onClick={() => onOpenFile(event.file)}>
                    <FileText size={13} />
                    Open file
                  </button>
                  <button type="button" onClick={() => onOpenFile(event.file, true)}>
                    <FolderOpen size={13} />
                    Open folder
                  </button>
                </div>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function AgentList({ agents, activeNode }) {
  if (!agents.length) {
    return <p className="empty">No agent state available.</p>;
  }

  return (
    <div className="agentGrid">
      {agents.map((agent) => (
        <article className={`agentCard ${agent.status}`} key={agent.name}>
          <Bot size={18} />
          <div>
            <strong>{agent.name}</strong>
            <p>{agent.node === activeNode ? "Current graph node" : agent.role}</p>
          </div>
          <span className="tag">{agent.status}</span>
        </article>
      ))}
    </div>
  );
}

function HelpView({ markdown, onBack }) {
  const headings = extractHeadings(markdown);

  return (
    <section className="helpLayout">
      <aside className="helpNav panel">
        <button className="backButton" type="button" onClick={onBack}>
          <ArrowLeft size={16} />
          Dashboard
        </button>
        <p className="eyebrow">Help</p>
        <nav>
          {headings.map((heading) => (
            <a className={`helpNavLink level-${heading.level}`} href={`#${heading.id}`} key={heading.id}>
              {heading.text}
            </a>
          ))}
        </nav>
      </aside>
      <section className="helpPanel panel">
        <MarkdownView markdown={markdown} />
      </section>
    </section>
  );
}

function MarkdownView({ markdown }) {
  const lines = markdown.split("\n");
  const elements = [];
  let codeBlock = [];
  let inCode = false;
  let listItems = [];

  const flushList = () => {
    if (listItems.length) {
      elements.push(<ul key={`list-${elements.length}`}>{listItems}</ul>);
      listItems = [];
    }
  };

  const flushCode = () => {
    if (codeBlock.length) {
      elements.push(<pre className="helpCode" key={`code-${elements.length}`}>{codeBlock.join("\n")}</pre>);
      codeBlock = [];
    }
  };

  lines.forEach((line, index) => {
    if (line.startsWith("```")) {
      if (inCode) {
        inCode = false;
        flushCode();
      } else {
        flushList();
        inCode = true;
      }
      return;
    }

    if (inCode) {
      codeBlock.push(line);
      return;
    }

    if (line.startsWith("# ")) {
      flushList();
      const text = line.slice(2);
      elements.push(<h1 id={headingId(text)} key={index}>{text}</h1>);
    } else if (line.startsWith("## ")) {
      flushList();
      const text = line.slice(3);
      elements.push(<h2 id={headingId(text)} key={index}>{text}</h2>);
    } else if (line.startsWith("### ")) {
      flushList();
      const text = line.slice(4);
      elements.push(<h3 id={headingId(text)} key={index}>{text}</h3>);
    } else if (line.startsWith("- ")) {
      listItems.push(<li key={index}>{renderInline(line.slice(2))}</li>);
    } else if (line.trim()) {
      flushList();
      elements.push(<p key={index}>{renderInline(line)}</p>);
    }
  });

  flushList();
  flushCode();

  return <article className="helpContent">{elements}</article>;
}

function extractHeadings(markdown) {
  return markdown
    .split("\n")
    .filter((line) => line.startsWith("# ") || line.startsWith("## ") || line.startsWith("### "))
    .map((line) => {
      const level = line.startsWith("### ") ? 3 : line.startsWith("## ") ? 2 : 1;
      const text = line.replace(/^#{1,3}\s+/, "");
      return { level, text, id: headingId(text) };
    });
}

function headingId(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function renderInline(text) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function formatRunState(status) {
  if (status === "running") {
    return "Running";
  }
  if (status === "stopping") {
    return "Stopping";
  }
  if (status === "completed") {
    return "Completed";
  }
  if (status === "failed") {
    return "Failed";
  }
  if (status === "stopped") {
    return "Stopped";
  }
  return "Idle";
}

function runtimeHint(status, nextNode) {
  if (status === "running") {
    return nextNode ? `Graph checkpoint is at ${nextNode}. Watch Activity for model and tool calls.` : "The runner is working. Activity updates appear as each step starts.";
  }
  if (status === "stopping") {
    return "Stop has been requested. The current graph step will finish first.";
  }
  if (status === "completed") {
    return "Last run finished.";
  }
  return nextNode ? `Checkpoint is waiting at ${nextNode}. Click Run to continue.` : "Click Run to start or resume the workflow.";
}

function modeLabel(mode) {
  if (mode === "rapid") {
    return "Rapid";
  }
  if (mode === "vibe") {
    return "Vibe";
  }
  return "Spec-gate";
}

const MODE_OPTIONS = [
  {
    value: "spec-gate",
    label: "Spec-gate",
    short: "Strict",
    description: "Requires successful tool calls and passing tests before completing a task.",
  },
  {
    value: "rapid",
    label: "Rapid",
    short: "Test, then move",
    description: "Requires successful tool calls, runs tests, and still completes if tests fail.",
  },
  {
    value: "vibe",
    label: "Vibe",
    short: "No tests",
    description: "Requires successful tool calls, then completes the task without running tests.",
  },
];

createRoot(document.getElementById("root")).render(<App />);
