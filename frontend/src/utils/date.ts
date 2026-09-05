/**
 * Date and Time formatting utilities for BUS-CV.
 * Standardizes operational timestamps to Asia/Kolkata (IST) timezone.
 */

export function formatIST(
  dateInput: string | number | Date | null | undefined,
  includeTime = true
): string {
  if (!dateInput) return '—';

  try {
    const date = typeof dateInput === 'string' || typeof dateInput === 'number'
      ? new Date(dateInput)
      : dateInput;

    if (isNaN(date.getTime())) return '—';

    // Format using Intl.DateTimeFormat with Asia/Kolkata timezone
    const options: Intl.DateTimeFormatOptions = {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      ...(includeTime
        ? {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true,
          }
        : {}),
    };

    const formatted = new Intl.DateTimeFormat('en-IN', options).format(date);
    return includeTime ? `${formatted} IST` : formatted;
  } catch {
    return '—';
  }
}

export function formatISTTimeOnly(dateInput: string | number | Date | null | undefined): string {
  if (!dateInput) return '—';

  try {
    const date = typeof dateInput === 'string' || typeof dateInput === 'number'
      ? new Date(dateInput)
      : dateInput;

    if (isNaN(date.getTime())) return '—';

    const options: Intl.DateTimeFormatOptions = {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    };

    return `${new Intl.DateTimeFormat('en-IN', options).format(date)} IST`;
  } catch {
    return '—';
  }
}
