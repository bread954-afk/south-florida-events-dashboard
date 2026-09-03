(function (global) {
  'use strict';

  function pad(value) {
    return String(value).padStart(2, '0');
  }

  function compactDate(dateString) {
    return String(dateString || '').replace(/-/g, '');
  }

  function nextDateCompact(dateString) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dateString || ''));
    if (!match) return '';
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + 1));
    return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}`;
  }

  function escapeIcsText(value) {
    return String(value || '')
      .replace(/\\/g, '\\\\')
      .replace(/\r?\n/g, '\\n')
      .replace(/,/g, '\\,')
      .replace(/;/g, '\\;');
  }

  function parseClock(value) {
    const match = /\b(1[0-2]|0?[1-9]):([0-5]\d)\s*([AP]M)\b/i.exec(String(value || ''));
    if (!match) return null;
    let hour = Number(match[1]);
    const minute = Number(match[2]);
    const ampm = match[3].toUpperCase();
    if (ampm === 'AM' && hour === 12) hour = 0;
    if (ampm === 'PM' && hour !== 12) hour += 12;
    return { hour, minute };
  }

  function formatLocalDateTime(dateString, clock) {
    return `${compactDate(dateString)}T${pad(clock.hour)}${pad(clock.minute)}00`;
  }

  function plusMinutes(clock, minutes) {
    const total = clock.hour * 60 + clock.minute + minutes;
    const dayOffset = Math.floor(total / (24 * 60));
    const normalized = ((total % (24 * 60)) + (24 * 60)) % (24 * 60);
    return {
      hour: Math.floor(normalized / 60),
      minute: normalized % 60,
      dayOffset,
    };
  }

  function addDays(dateString, days) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(dateString || ''));
    if (!match) return dateString;
    const date = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]) + days));
    return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
  }

  function timingFor(event) {
    const date = String(event.date || '');
    const timeText = String(event.time || '').trim();
    const start = parseClock(timeText);
    if (!start) {
      return {
        allDay: true,
        start: compactDate(date),
        end: nextDateCompact(date),
      };
    }

    const clocks = [...timeText.matchAll(/\b(1[0-2]|0?[1-9]):([0-5]\d)\s*([AP]M)\b/ig)]
      .map(match => parseClock(match[0]));

    let end;
    let endDate = date;
    if (clocks.length >= 2) {
      end = clocks[1];
      const startMinutes = start.hour * 60 + start.minute;
      const endMinutes = end.hour * 60 + end.minute;
      if (endMinutes <= startMinutes) endDate = addDays(date, 1);
    } else {
      const added = plusMinutes(start, 120);
      end = { hour: added.hour, minute: added.minute };
      if (added.dayOffset) endDate = addDays(date, added.dayOffset);
    }

    return {
      allDay: false,
      start: formatLocalDateTime(date, start),
      end: formatLocalDateTime(endDate, end),
    };
  }

  function buildIcs(event) {
    const timing = timingFor(event);
    const location = [event.venue, event.city].filter(Boolean).join(', ');
    const descriptionParts = [];
    if (event.category) descriptionParts.push(`Category: ${event.category}`);
    if (event.cost) descriptionParts.push(`Cost: ${event.cost}`);
    if (event.age) descriptionParts.push(`Age: ${event.age}`);
    if (event.url) descriptionParts.push(`Event / Tickets: ${event.url}`);

    const lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//South Florida Events Radar//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
    ];

    if (timing.allDay) {
      lines.push(`DTSTART;VALUE=DATE:${timing.start}`);
      lines.push(`DTEND;VALUE=DATE:${timing.end}`);
    } else {
      lines.push(`DTSTART:${timing.start}`);
      lines.push(`DTEND:${timing.end}`);
    }

    lines.push(`SUMMARY:${escapeIcsText(event.name || 'Event')}`);
    if (location) lines.push(`LOCATION:${escapeIcsText(location)}`);
    if (descriptionParts.length) lines.push(`DESCRIPTION:${escapeIcsText(descriptionParts.join('\n'))}`);
    if (event.url) lines.push(`URL:${String(event.url)}`);
    lines.push('END:VEVENT', 'END:VCALENDAR');
    return `${lines.join('\r\n')}\r\n`;
  }

  function calendarFilename(event) {
    const base = String(event && event.name ? event.name : 'event')
      .replace(/&/g, '')
      .replace(/[^A-Za-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .replace(/-+/g, '-');
    return `${base || 'event'}.ics`;
  }

  function downloadEvent(event) {
    if (typeof document === 'undefined' || typeof URL === 'undefined' || typeof Blob === 'undefined') {
      return false;
    }
    const blob = new Blob([buildIcs(event)], { type: 'text/calendar;charset=utf-8' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = calendarFilename(event);
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
    return true;
  }

  const api = { buildIcs, calendarFilename, downloadEvent, timingFor };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.SFCalendar = api;
})(typeof window !== 'undefined' ? window : globalThis);
