import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  X,
  Edit2,
  Save,
  Trash2,
  RefreshCw,
  Check,
  Clock,
  AlertCircle,
  Link as LinkIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  createTodo as createTodoApi,
  updateTodo as updateTodoApi,
  deleteTodo as deleteTodoApi,
  resyncTodo as resyncTodoApi,
  UpdateTodoRequest,
} from "../api";

interface Todo {
  id: number;
  title: string;
  due_hint: string | null;
  confidence: number | null;
  status: string;
  source_excerpt: string | null;
  ticktick_sync_status: string;
  ticktick_task_id: string | null;
  created_at: string;
  updated_at: string;
}

interface TaskManagerProps {
  sessionId: number;
  todos: Todo[];
  onUpdate: () => void;
}

const TaskManager: React.FC<TaskManagerProps> = ({
  sessionId,
  todos,
  onUpdate,
}) => {
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [newTask, setNewTask] = useState({
    title: "",
    due_hint: "",
    source_excerpt: "",
  });
  const [editTask, setEditTask] = useState<Partial<Todo>>({});
  const [isLoading, setIsLoading] = useState(false);

  const handleAdd = async () => {
    if (!newTask.title.trim()) {
      alert("Please enter a task title");
      return;
    }

    setIsLoading(true);
    try {
      await createTodoApi(sessionId, {
        title: newTask.title,
        due_hint: newTask.due_hint || undefined,
        source_excerpt: newTask.source_excerpt || undefined,
      });
      setNewTask({ title: "", due_hint: "", source_excerpt: "" });
      setIsAdding(false);
      onUpdate();
    } catch (error) {
      alert("Failed to create task. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdate = async (id: number) => {
    setIsLoading(true);
    try {
      const payload: UpdateTodoRequest = {};
      if (typeof editTask.title === "string") {
        payload.title = editTask.title;
      }
      if (typeof editTask.due_hint === "string") {
        payload.due_hint = editTask.due_hint;
      }
      if (typeof editTask.status === "string") {
        payload.status = editTask.status;
      }
      if (typeof editTask.source_excerpt === "string") {
        payload.source_excerpt = editTask.source_excerpt;
      }

      await updateTodoApi(id, payload);
      setEditingId(null);
      setEditTask({});
      onUpdate();
    } catch (error) {
      alert("Failed to update task. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id: number, title: string) => {
    if (!confirm(`Delete task "${title}"?`)) return;

    setIsLoading(true);
    try {
      await deleteTodoApi(id);
      onUpdate();
    } catch (error) {
      alert("Failed to delete task. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResync = async (id: number) => {
    setIsLoading(true);
    try {
      await resyncTodoApi(id);
      alert("Task queued for re-sync");
      onUpdate();
    } catch (error) {
      alert("Failed to resync task. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const startEdit = (todo: Todo) => {
    setEditingId(todo.id);
    setEditTask({
      title: todo.title,
      due_hint: todo.due_hint || "",
      status: todo.status,
    });
  };

  const getSyncStatusBadge = (syncStatus: string, taskId: string | null) => {
    const configs: Record<
      string,
      { icon: any; bg: string; text: string; label: string }
    > = {
      synced: {
        icon: Check,
        bg: "bg-green/20",
        text: "text-green",
        label: "Synced",
      },
      pending: {
        icon: Clock,
        bg: "bg-gold/20",
        text: "text-gold",
        label: "Pending",
      },
      error: {
        icon: AlertCircle,
        bg: "bg-red-500/20",
        text: "text-red-500",
        label: "Error",
      },
    };

    const config = configs[syncStatus] || configs.pending;
    const Icon = config.icon;

    return (
      <span
        className={cn(
          "flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium",
          config.bg,
          config.text,
        )}
      >
        <Icon size={12} />
        {config.label}
        {taskId && (
          <span title={`TickTick ID: ${taskId}`}>
            <LinkIcon size={10} className="opacity-60" />
          </span>
        )}
      </span>
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-display font-semibold text-bone flex items-center gap-2">
          📋 Tasks ({todos.length})
        </h4>
        <motion.button
          className={cn(
            "px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
            isAdding
              ? "border border-bone-dim text-bone-dim hover:bg-white/5"
              : "bg-gradient-green text-black hover:shadow-lg hover:shadow-green/50",
          )}
          onClick={() => setIsAdding(!isAdding)}
          disabled={isLoading}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {isAdding ? (
            <>
              <X size={14} />
              Cancel
            </>
          ) : (
            <>
              <Plus size={14} />
              Add Task
            </>
          )}
        </motion.button>
      </div>

      <AnimatePresence>
        {isAdding && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-black/30 border border-gold/20 rounded-lg p-4 space-y-3"
          >
            <input
              type="text"
              className="w-full bg-black border border-gold/20 rounded-lg px-3 py-2 text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
              placeholder="Task title *"
              value={newTask.title}
              onChange={(e) =>
                setNewTask({ ...newTask, title: e.target.value })
              }
              autoFocus
            />
            <input
              type="text"
              className="w-full bg-black border border-bone-dim/20 rounded-lg px-3 py-2 text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
              placeholder="Due hint (e.g., 'by Friday')"
              value={newTask.due_hint}
              onChange={(e) =>
                setNewTask({ ...newTask, due_hint: e.target.value })
              }
            />
            <textarea
              className="w-full bg-black border border-bone-dim/20 rounded-lg px-3 py-2 text-bone text-sm resize-y focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
              placeholder="Context (optional)"
              value={newTask.source_excerpt}
              onChange={(e) =>
                setNewTask({ ...newTask, source_excerpt: e.target.value })
              }
              rows={2}
            />
            <div className="flex gap-2 justify-end">
              <motion.button
                className="px-3 py-1.5 border border-bone-dim text-bone-dim rounded-lg text-sm font-medium hover:bg-white/5 transition-colors"
                onClick={() => setIsAdding(false)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                Cancel
              </motion.button>
              <motion.button
                className={cn(
                  "px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-all",
                  !newTask.title.trim() || isLoading
                    ? "bg-black-soft text-bone-dim cursor-not-allowed"
                    : "bg-gradient-green text-black hover:shadow-lg hover:shadow-green/50",
                )}
                onClick={handleAdd}
                disabled={isLoading || !newTask.title.trim()}
                whileHover={
                  newTask.title.trim() && !isLoading ? { scale: 1.05 } : {}
                }
                whileTap={
                  newTask.title.trim() && !isLoading ? { scale: 0.95 } : {}
                }
              >
                {isLoading ? "Creating..." : "Create Task"}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="space-y-2">
        {todos.length === 0 && !isAdding && (
          <div className="bg-black/20 border border-bone-dim/20 rounded-lg p-6 text-center space-y-2">
            <p className="text-bone-dim text-sm">No tasks found</p>
            <p className="text-bone-dim text-xs">
              Add tasks manually or they'll be extracted from your audio
            </p>
          </div>
        )}

        {todos.map((todo, idx) => (
          <motion.div
            key={todo.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className={cn(
              "bg-black/30 border border-bone-dim/20 rounded-lg p-3",
              editingId !== todo.id && "flex items-start gap-3",
            )}
          >
            {editingId === todo.id ? (
              <div className="space-y-3">
                <input
                  type="text"
                  className="w-full bg-black border border-gold/20 rounded-lg px-3 py-2 text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
                  value={editTask.title || ""}
                  onChange={(e) =>
                    setEditTask({ ...editTask, title: e.target.value })
                  }
                  onClick={(e) => e.stopPropagation()}
                  onFocus={(e) => e.stopPropagation()}
                />
                <input
                  type="text"
                  className="w-full bg-black border border-bone-dim/20 rounded-lg px-3 py-2 text-bone text-sm focus:outline-none focus:border-gold focus:ring-2 focus:ring-gold/20"
                  placeholder="Due hint"
                  value={editTask.due_hint || ""}
                  onChange={(e) =>
                    setEditTask({ ...editTask, due_hint: e.target.value })
                  }
                  onClick={(e) => e.stopPropagation()}
                  onFocus={(e) => e.stopPropagation()}
                />
                <div className="flex gap-2 justify-end">
                  <motion.button
                    className="px-2 py-1 border border-bone-dim text-bone-dim rounded text-xs font-medium hover:bg-white/5"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(null);
                      setEditTask({});
                    }}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Cancel
                  </motion.button>
                  <motion.button
                    className="px-2 py-1 bg-gradient-green text-black rounded text-xs font-medium hover:shadow-lg disabled:opacity-50"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUpdate(todo.id);
                    }}
                    disabled={isLoading}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    Save
                  </motion.button>
                </div>
              </div>
            ) : (
              <>
                <div className="space-y-2 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <h5 className="text-sm font-medium text-bone flex-1">
                      {todo.title}
                    </h5>
                    {getSyncStatusBadge(
                      todo.ticktick_sync_status,
                      todo.ticktick_task_id,
                    )}
                  </div>

                  {todo.due_hint && (
                    <div className="text-xs text-gold flex items-center gap-1.5">
                      <Clock size={12} />
                      {todo.due_hint}
                    </div>
                  )}

                  {todo.source_excerpt && (
                    <div className="text-xs text-bone-dim italic bg-black/30 p-2 rounded border-l-2 border-green/30">
                      💬 "{todo.source_excerpt}"
                    </div>
                  )}

                  {todo.confidence !== null && (
                    <div
                      className={cn(
                        "text-xs font-medium flex items-center gap-1.5",
                        todo.confidence >= 0.9
                          ? "text-green"
                          : todo.confidence >= 0.8
                            ? "text-gold"
                            : "text-bone-dim",
                      )}
                    >
                      🎯 {Math.round(todo.confidence * 100)}% confidence
                    </div>
                  )}
                </div>

                <div className="flex gap-1">
                  <motion.button
                    className="p-1.5 text-blue hover:bg-blue/10 rounded transition-colors disabled:opacity-50"
                    onClick={(e) => {
                      e.stopPropagation();
                      startEdit(todo);
                    }}
                    title="Edit task"
                    disabled={isLoading}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <Edit2 size={14} />
                  </motion.button>
                  {todo.ticktick_sync_status === "error" && (
                    <motion.button
                      className="p-1.5 text-gold hover:bg-gold/10 rounded transition-colors disabled:opacity-50"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleResync(todo.id);
                      }}
                      title="Retry sync"
                      disabled={isLoading}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                    >
                      <RefreshCw size={14} />
                    </motion.button>
                  )}
                  <motion.button
                    className="p-1.5 text-red-500 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(todo.id, todo.title);
                    }}
                    title="Delete task"
                    disabled={isLoading}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                  >
                    <Trash2 size={14} />
                  </motion.button>
                </div>
              </>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default TaskManager;
