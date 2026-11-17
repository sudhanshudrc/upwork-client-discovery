import * as React from 'react';
import {
  Calendar,
  Clock,
  Mail,
  Plus,
  X,
  Play,
  Pause,
  Trash2,
  Edit2,
  Check,
  AlertCircle,
  Loader2,
  RefreshCw,
  Globe,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/components/ui/utils';
import {
  api,
  type ScheduleResponse,
  type ScheduleCreateRequest,
  type ScheduleUpdateRequest,
  getStoredUserIdentifier,
} from '@/services/api';

const DAYS_OF_WEEK: { id: string; label: string }[] = [
  { id: 'mon', label: 'Mon' },
  { id: 'tue', label: 'Tue' },
  { id: 'wed', label: 'Wed' },
  { id: 'thu', label: 'Thu' },
  { id: 'fri', label: 'Fri' },
  { id: 'sat', label: 'Sat' },
  { id: 'sun', label: 'Sun' },
];

interface ScheduleManagerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  defaultKeyword?: string;
}

export function ScheduleManagerDialog({
  open,
  onOpenChange,
  defaultKeyword = 'AI Engineer',
}: ScheduleManagerDialogProps) {
  const userIdentifier = getStoredUserIdentifier() || 'default';

  // Schedule Form State
  const [keyword, setKeyword] = React.useState(defaultKeyword);
  const [selectedDays, setSelectedDays] = React.useState<string[]>([]);
  const [time, setTime] = React.useState('10:30');
  const [timezone, setTimezone] = React.useState('Asia/Kolkata');
  const [recipientEmails, setRecipientEmails] = React.useState<string[]>([]);
  const [emailInput, setEmailInput] = React.useState('');
  const [targetLimit, setTargetLimit] = React.useState(10);
  const [minDelay, setMinDelay] = React.useState(30);
  const [maxDelay, setMaxDelay] = React.useState(120);

  // Edit Mode & State
  const [editingScheduleId, setEditingScheduleId] = React.useState<string | null>(null);

  // Schedules List State
  const [schedules, setSchedules] = React.useState<ScheduleResponse[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [actionLoadingId, setActionLoadingId] = React.useState<string | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);
  const [successMessage, setSuccessMessage] = React.useState<string | null>(null);

  // Initialize timezone from browser on mount
  React.useEffect(() => {
    try {
      const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (userTz) {
        setTimezone(userTz);
      }
    } catch {
      setTimezone('Asia/Kolkata');
    }
  }, []);

  // Update default keyword when prop changes if form not modified
  React.useEffect(() => {
    if (!editingScheduleId && defaultKeyword) {
      setKeyword(defaultKeyword);
    }
  }, [defaultKeyword, editingScheduleId]);

  // Load schedules whenever dialog opens
  const fetchSchedules = React.useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const list = await api.listSchedules(userIdentifier);
      setSchedules(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load schedules.';
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  }, [userIdentifier]);

  React.useEffect(() => {
    if (open) {
      fetchSchedules();
    }
  }, [open, fetchSchedules]);

  // Day toggle handler
  const handleToggleDay = (dayId: string) => {
    setSelectedDays((prev) =>
      prev.includes(dayId) ? prev.filter((d) => d !== dayId) : [...prev, dayId]
    );
  };

  // Email chip addition
  const handleAddEmail = () => {
    const trimmed = emailInput.trim().toLowerCase();
    if (!trimmed) return;

    // Simple email format check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) {
      setErrorMessage('Please enter a valid email address.');
      return;
    }

    if (!recipientEmails.includes(trimmed)) {
      setRecipientEmails((prev) => [...prev, trimmed]);
    }
    setEmailInput('');
    setErrorMessage(null);
  };

  const handleRemoveEmail = (target: string) => {
    setRecipientEmails((prev) => prev.filter((e) => e !== target));
  };

  // Reset form
  const handleResetForm = () => {
    setEditingScheduleId(null);
    setKeyword(defaultKeyword || 'AI Engineer');
    setSelectedDays([]);
    setTime('10:30');
    setRecipientEmails([]);
    setEmailInput('');
    setTargetLimit(10);
    setMinDelay(30);
    setMaxDelay(120);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  // Start editing existing schedule
  const handleStartEdit = (sched: ScheduleResponse) => {
    setEditingScheduleId(sched.id);
    setKeyword(sched.search_keyword);
    setSelectedDays(sched.selected_days || []);
    setTime(sched.execution_time || '10:30');
    setTimezone(sched.timezone || 'Asia/Kolkata');
    setRecipientEmails(sched.recipient_emails || []);
    setTargetLimit(sched.target_limit || 10);
    setMinDelay(sched.min_delay_seconds || 30);
    setMaxDelay(sched.max_delay_seconds || 120);
    setErrorMessage(null);
    setSuccessMessage(null);
  };

  // Save / Submit Schedule
  const handleSubmitSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!keyword.trim()) {
      setErrorMessage('Search keyword is required.');
      return;
    }

    if (selectedDays.length === 0) {
      setErrorMessage('Please select at least one active day of the week.');
      return;
    }

    if (recipientEmails.length === 0 && !emailInput.trim()) {
      setErrorMessage('Please specify at least one recipient email address.');
      return;
    }

    // Auto-add pending email text if typed but not confirmed
    let finalEmails = [...recipientEmails];
    if (emailInput.trim()) {
      const trimmed = emailInput.trim().toLowerCase();
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (emailRegex.test(trimmed) && !finalEmails.includes(trimmed)) {
        finalEmails = [...finalEmails, trimmed];
        setEmailInput('');
      }
    }

    setIsSubmitting(true);
    try {
      if (editingScheduleId) {
        const payload: ScheduleUpdateRequest = {
          search_keyword: keyword.trim(),
          execution_time: time,
          selected_days: selectedDays,
          timezone: timezone,
          target_limit: targetLimit,
          min_delay_seconds: minDelay,
          max_delay_seconds: maxDelay,
          recipient_emails: finalEmails,
        };
        await api.updateSchedule(editingScheduleId, payload);
        setSuccessMessage('Schedule updated successfully.');
      } else {
        const payload: ScheduleCreateRequest = {
          search_keyword: keyword.trim(),
          target_limit: targetLimit,
          frequency_type: 'CRON',
          execution_time: time,
          selected_days: selectedDays,
          timezone: timezone,
          min_delay_seconds: minDelay,
          max_delay_seconds: maxDelay,
          recipient_emails: finalEmails,
        };
        await api.createSchedule(payload, userIdentifier);
        setSuccessMessage('New recurring schedule created successfully.');
      }

      handleResetForm();
      await fetchSchedules();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error saving schedule.';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Run Now (Immediate Celery Dispatch)
  const handleTriggerNow = async (schedId: string) => {
    setActionLoadingId(schedId);
    setErrorMessage(null);
    try {
      const res = await api.triggerScheduleNow(schedId);
      setSuccessMessage(`Immediate execution dispatched (Task ID: ${res.task_id}).`);
      await fetchSchedules();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to trigger schedule execution.';
      setErrorMessage(msg);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Toggle Pause / Resume
  const handleToggleActive = async (sched: ScheduleResponse) => {
    setActionLoadingId(sched.id);
    setErrorMessage(null);
    try {
      await api.updateSchedule(sched.id, { is_active: !sched.is_active });
      await fetchSchedules();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update schedule status.';
      setErrorMessage(msg);
    } finally {
      setActionLoadingId(null);
    }
  };

  // Delete Schedule
  const handleDeleteSchedule = async (schedId: string) => {
    if (!window.confirm('Are you sure you want to delete this schedule? Historical execution logs will also be deleted.')) {
      return;
    }
    setActionLoadingId(schedId);
    setErrorMessage(null);
    try {
      await api.deleteSchedule(schedId);
      if (editingScheduleId === schedId) {
        handleResetForm();
      }
      await fetchSchedules();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete schedule.';
      setErrorMessage(msg);
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 p-6 space-y-6">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <DialogTitle className="text-xl font-bold flex items-center gap-2">
                <Calendar className="size-5 text-blue-600 dark:text-blue-400" />
                Scheduled Lead Automation & Email Delivery
              </DialogTitle>
              <DialogDescription className="text-xs text-slate-500 dark:text-slate-400">
                Configure automated keyword searches running with sequential human pacing (0.5 - 2.0 min jitter) and diagnostic Excel email delivery.
              </DialogDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchSchedules}
              disabled={isLoading}
              className="text-xs gap-1.5"
            >
              <RefreshCw className={cn('size-3.5', isLoading && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </DialogHeader>

        {/* Status Alerts */}
        {errorMessage && (
          <div className="rounded-lg border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-red-950/40 p-3 flex items-start gap-2.5 text-xs text-red-700 dark:text-red-300">
            <AlertCircle className="size-4 shrink-0 mt-0.5 text-red-600 dark:text-red-400" />
            <div className="flex-1">{errorMessage}</div>
          </div>
        )}

        {successMessage && (
          <div className="rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-950/40 p-3 flex items-start gap-2.5 text-xs text-emerald-700 dark:text-emerald-300">
            <Check className="size-4 shrink-0 mt-0.5 text-emerald-600 dark:text-emerald-400" />
            <div className="flex-1">{successMessage}</div>
          </div>
        )}

        {/* 1. Schedule Configuration Form */}
        <form onSubmit={handleSubmitSchedule} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 p-4 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300 flex items-center gap-1.5">
              {editingScheduleId ? <Edit2 className="size-3.5" /> : <Plus className="size-3.5" />}
              {editingScheduleId ? 'Edit Recurring Schedule' : 'Create New Recurring Schedule'}
            </span>
            {editingScheduleId && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleResetForm}
                className="text-xs h-7 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              >
                Cancel Edit
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Search Keyword */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Search Keyword <span className="text-red-500">*</span>
              </label>
              <Input
                type="text"
                placeholder="e.g. AI Engineer, Next.js Developer"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="text-xs"
                required
              />
            </div>

            {/* Target Job Limit */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Target Harvest Limit (Jobs per run)
              </label>
              <Input
                type="number"
                min={1}
                max={50}
                value={targetLimit}
                onChange={(e) => setTargetLimit(Number(e.target.value))}
                className="text-xs"
              />
            </div>
          </div>

          {/* Active Days of Week (7 Multi-select Pill Buttons) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Calendar className="size-3.5 text-blue-500" />
                Active Days of Week <span className="text-red-500">*</span>
              </label>
              <span className="text-[11px] text-slate-500 dark:text-slate-400">
                {selectedDays.length} of 7 days selected
              </span>
            </div>
            <div className="flex flex-wrap gap-2">
              {DAYS_OF_WEEK.map((day) => {
                const isSelected = selectedDays.includes(day.id);
                return (
                  <button
                    key={day.id}
                    type="button"
                    onClick={() => handleToggleDay(day.id)}
                    className={cn(
                      'px-3.5 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer',
                      isSelected
                        ? 'bg-blue-600 border-blue-600 text-white shadow-xs'
                        : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    )}
                  >
                    {day.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Execution Time & Timezone */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Clock className="size-3.5 text-blue-500" />
                Target Execution Time (HH:mm)
              </label>
              <Input
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="text-xs"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Globe className="size-3.5 text-blue-500" />
                Timezone
              </label>
              <Input
                type="text"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                placeholder="e.g. Asia/Kolkata, America/New_York"
                className="text-xs"
                required
              />
            </div>
          </div>

          {/* Anti-Bot Human Pacing Jitter Bounds */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Min Delay Jitter Between Jobs (Seconds)
              </label>
              <Input
                type="number"
                min={5}
                max={300}
                value={minDelay}
                onChange={(e) => setMinDelay(Number(e.target.value))}
                className="text-xs"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Max Delay Jitter Between Jobs (Seconds)
              </label>
              <Input
                type="number"
                min={5}
                max={600}
                value={maxDelay}
                onChange={(e) => setMaxDelay(Number(e.target.value))}
                className="text-xs"
              />
            </div>
          </div>

          {/* Recipient Email Chip Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Mail className="size-3.5 text-blue-500" />
              Recipient Email Addresses <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-2">
              <Input
                type="email"
                placeholder="Enter email and press Enter or Add"
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddEmail();
                  }
                }}
                className="text-xs flex-1"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddEmail}
                className="text-xs gap-1"
              >
                <Plus className="size-3.5" />
                Add
              </Button>
            </div>

            {recipientEmails.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {recipientEmails.map((email) => (
                  <Badge
                    key={email}
                    variant="brand"
                    className="gap-1.5 text-xs py-1 px-2.5 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
                  >
                    {email}
                    <button
                      type="button"
                      onClick={() => handleRemoveEmail(email)}
                      className="hover:text-red-600 dark:hover:text-red-400 cursor-pointer"
                      title="Remove recipient"
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="text-xs gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  Saving...
                </>
              ) : editingScheduleId ? (
                <>
                  <Check className="size-3.5" />
                  Update Schedule
                </>
              ) : (
                <>
                  <Plus className="size-3.5" />
                  Save Schedule
                </>
              )}
            </Button>
          </div>
        </form>

        {/* 2. Existing Schedules Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
              Active & Configured Automations ({schedules.length})
            </span>
          </div>

          {isLoading ? (
            <div className="text-center py-8 text-xs text-slate-500 animate-pulse">
              Loading schedules...
            </div>
          ) : schedules.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 dark:border-slate-800 p-8 text-center space-y-2">
              <Calendar className="size-8 mx-auto text-slate-400" />
              <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                No automated search schedules configured
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                Use the form above to set up recurring searches for target keywords with automated Excel email delivery.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300">
                  <tr>
                    <th className="py-2.5 px-3 font-semibold">Keyword</th>
                    <th className="py-2.5 px-3 font-semibold">Days & Time</th>
                    <th className="py-2.5 px-3 font-semibold">Recipients</th>
                    <th className="py-2.5 px-3 font-semibold">Next Run</th>
                    <th className="py-2.5 px-3 font-semibold">Status</th>
                    <th className="py-2.5 px-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 text-slate-700 dark:text-slate-300">
                  {schedules.map((sched) => {
                    const isBusy = actionLoadingId === sched.id;
                    const nextRunFormatted = sched.next_run_at
                      ? new Date(sched.next_run_at).toLocaleString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : 'Not scheduled';

                    return (
                      <tr
                        key={sched.id}
                        className={cn(
                          'hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors',
                          editingScheduleId === sched.id && 'bg-blue-50/40 dark:bg-blue-950/20'
                        )}
                      >
                        <td className="py-3 px-3 font-semibold text-slate-900 dark:text-slate-100">
                          {sched.search_keyword}
                          <div className="text-[10px] text-slate-400">
                            Limit: {sched.target_limit} jobs &bull; Jitter: {sched.min_delay_seconds}s-{sched.max_delay_seconds}s
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="font-medium text-slate-800 dark:text-slate-200">
                            {sched.execution_time} ({sched.timezone?.split('/').pop() || sched.timezone})
                          </div>
                          <div className="flex gap-1 mt-0.5">
                            {(sched.selected_days || []).map((d) => (
                              <span
                                key={d}
                                className="inline-block text-[9px] uppercase px-1 py-0.2 bg-slate-200 dark:bg-slate-700 rounded font-semibold text-slate-700 dark:text-slate-300"
                              >
                                {d}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <div className="text-[11px] truncate max-w-[140px]" title={sched.recipient_emails?.join(', ')}>
                            {sched.recipient_emails?.length
                              ? `${sched.recipient_emails[0]}${
                                  sched.recipient_emails.length > 1
                                    ? ` +${sched.recipient_emails.length - 1}`
                                    : ''
                                }`
                              : 'None'}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-[11px] text-slate-600 dark:text-slate-400">
                          {nextRunFormatted}
                        </td>
                        <td className="py-3 px-3">
                          {sched.is_active ? (
                            <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20 text-[10px] py-0 px-2">
                              Active
                            </Badge>
                          ) : (
                            <Badge className="bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20 text-[10px] py-0 px-2">
                              Paused
                            </Badge>
                          )}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-1">
                            {/* Run Now */}
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={isBusy}
                              onClick={() => handleTriggerNow(sched.id)}
                              className="h-7 px-2 text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/40"
                              title="Trigger immediate Celery execution"
                            >
                              <Play className="size-3" />
                              <span className="sr-only">Run Now</span>
                            </Button>

                            {/* Pause / Resume */}
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={isBusy}
                              onClick={() => handleToggleActive(sched)}
                              className="h-7 px-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                              title={sched.is_active ? 'Pause Schedule' : 'Resume Schedule'}
                            >
                              {sched.is_active ? <Pause className="size-3" /> : <Play className="size-3" />}
                              <span className="sr-only">{sched.is_active ? 'Pause' : 'Resume'}</span>
                            </Button>

                            {/* Edit */}
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={isBusy}
                              onClick={() => handleStartEdit(sched)}
                              className="h-7 px-2 text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                              title="Edit Schedule"
                            >
                              <Edit2 className="size-3" />
                              <span className="sr-only">Edit</span>
                            </Button>

                            {/* Delete */}
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              disabled={isBusy}
                              onClick={() => handleDeleteSchedule(sched.id)}
                              className="h-7 px-2 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40"
                              title="Delete Schedule"
                            >
                              <Trash2 className="size-3" />
                              <span className="sr-only">Delete</span>
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
