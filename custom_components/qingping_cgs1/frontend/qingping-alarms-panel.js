const DOMAIN = "qingping_cgs1";
const WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const RINGTONES = [
  "Exotic Guitar",
  "Lively Piano",
  "Story Piano",
  "Beep",
  "Cuckoo",
  "Digital Ringtone",
  "Digital Ringtone 2",
  "Telephone Ringtone",
];
const DEFAULT_RINGTONE = "Lively Piano";
const PRESETS = [
  ["once", []],
  ["weekdays", ["mon", "tue", "wed", "thu", "fri"]],
  ["weekends", ["sat", "sun"]],
  ["every_day", WEEKDAYS],
];

const TEXT_KEYS = [
  "title",
  "add",
  "edit",
  "empty",
  "no_devices",
  "device",
  "time",
  "repeat",
  "ringtone",
  "snooze",
  "once",
  "weekdays",
  "weekends",
  "every_day",
  "save",
  "delete",
  "confirm_delete",
  "error",
];

const ICONS = {
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  alarm: "M12,20A7,7 0 0,1 5,13A7,7 0 0,1 12,6A7,7 0 0,1 19,13A7,7 0 0,1 12,20M12,4A9,9 0 0,0 3,13A9,9 0 0,0 12,22A9,9 0 0,0 21,13A9,9 0 0,0 12,4M12.5,8H11V14L15.75,16.85L16.5,15.62L12.5,13.25V8M7.88,3.39L6.6,1.86L2,5.71L3.29,7.24L7.88,3.39M22,5.72L17.4,1.86L16.11,3.39L20.71,7.25L22,5.72Z",
  alarmOff: "M10.04,6.29C10.66,6.11 11.32,6 12,6A7,7 0 0,1 19,13C19,13.68 18.89,14.34 18.71,14.96L20.25,16.5C20.73,15.43 21,14.25 21,13A9,9 0 0,0 12,4C10.75,4 9.57,4.27 8.5,4.75L10.04,6.29M7.89,3.36L6.6,1.86L5.31,2.95L6.73,4.37L7.89,3.36M2.39,2.27L1.11,3.54L2.05,4.5L2,4.54L3.28,6.06L4.37,5.15L5.12,5.9C3.79,7.47 3,9.47 3,11.67V13A9,9 0 0,0 12,22C14.32,22 16.44,21.13 18.04,19.69L20.24,21.89L21.5,20.62L2.39,2.27M12,20A7,7 0 0,1 5,13C5,11.08 5.77,9.34 7,8.07L16.62,17.69C15.36,19.12 13.76,20 12,20M22,5.72L17.4,1.86L16.11,3.39L20.71,7.25L22,5.72Z",
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  close: "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
};

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const sameDays = (a, b) => a.length === b.length && a.every((d) => b.includes(d));

const svgIcon = (path) => `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${path}"></path></svg>`;

const STYLES = `
  :host {
    display: block;
    min-height: 100vh;
    background-color: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif);
    -webkit-font-smoothing: var(--ha-font-smoothing, antialiased);
  }
  .toolbar {
    display: flex;
    align-items: center;
    height: var(--header-height, 56px);
    padding: 0 12px;
    box-sizing: border-box;
    background-color: var(--app-header-background-color);
    color: var(--app-header-text-color, white);
    border-bottom: var(--app-header-border-bottom, none);
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-normal, 400);
    position: sticky;
    top: 0;
    z-index: 4;
  }
  .toolbar .main-title {
    margin-inline-start: 24px;
    line-height: var(--ha-line-height-normal, 20px);
    flex-grow: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .toolbar.narrow .main-title { margin-inline-start: 4px; }
  .fallback-menu {
    background: none; border: none; color: inherit; cursor: pointer; padding: 8px;
    border-radius: 50%; display: inline-flex;
  }
  .fallback-menu svg { width: 24px; height: 24px; fill: currentColor; }
  .content {
    max-width: 600px;
    margin: 0 auto;
    padding: 28px 20px 96px;
    box-sizing: border-box;
  }
  :host([narrow]) .content { padding: 16px 8px 96px; }
  ha-card { display: block; margin-bottom: 24px; }
  ha-card:not(:defined) {
    background: var(--ha-card-background, var(--card-background-color, white));
    border-radius: var(--ha-card-border-radius, 12px);
    border: var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
    box-shadow: var(--ha-card-box-shadow, none);
  }
  .card-header {
    color: var(--ha-card-header-color, var(--primary-text-color));
    font-size: var(--ha-card-header-font-size, var(--ha-font-size-2xl, 24px));
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: var(--ha-line-height-condensed, 32px);
    padding: 24px 16px 16px;
    letter-spacing: -0.012em;
  }
  .card-content { padding: 0 0 8px; }
  .row {
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 56px;
    padding: 4px 16px;
    cursor: pointer;
    position: relative;
  }
  .ripple {
    position: absolute;
    inset: 0;
    overflow: hidden;
    border-radius: inherit;
    pointer-events: none;
  }
  .ripple::before, .ripple .press {
    position: absolute;
    opacity: 0;
  }
  .ripple::before {
    content: "";
    inset: 0;
    background-color: var(--ha-ripple-hover-color, var(--ha-ripple-color, var(--secondary-text-color)));
    transition: opacity 15ms linear, background-color 15ms linear;
  }
  @media (hover: hover) {
    :hover > .ripple::before { opacity: var(--ha-ripple-hover-opacity, 0.08); }
  }
  .ripple .press {
    top: 0;
    left: 0;
    transform-origin: center center;
    background: radial-gradient(
      closest-side,
      var(--ha-ripple-pressed-color, var(--ha-ripple-color, var(--secondary-text-color))) max(100% - 70px, 65%),
      transparent 100%
    );
    transition-property: opacity, transform;
    transition-duration: 375ms, 450ms;
    transition-timing-function: linear, cubic-bezier(0.2, 0, 0, 1);
  }
  .pressed > .ripple .press {
    opacity: var(--ha-ripple-pressed-opacity, 0.12);
    transition-duration: 105ms, 450ms;
  }
  @media (prefers-reduced-motion: reduce) {
    .ripple .press { transition-property: opacity; }
  }
  .row .icon {
    width: 40px;
    height: 40px;
    flex: none;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--state-icon-color, #44739e);
    transition: color 0.3s ease-in-out, filter 0.3s ease-in-out;
  }
  .row.on .icon { color: var(--state-active-color, var(--amber-color, #ffc107)); }
  .row .icon svg { width: 24px; height: 24px; fill: currentColor; }
  .row .info { flex: 1; min-width: 0; }
  .row .primary {
    font-size: var(--ha-font-size-l, 16px);
    line-height: 24px;
    font-variant-numeric: tabular-nums;
  }
  .row .secondary {
    color: var(--secondary-text-color);
    font-size: var(--ha-font-size-m, 14px);
    line-height: 20px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .empty {
    color: var(--secondary-text-color);
    padding: 8px 16px 16px;
  }
  .switch-fallback { position: relative; width: 36px; height: 14px; flex: none; margin: 0 4px; }
  .switch-fallback input { position: absolute; inset: -12px; opacity: 0; margin: 0; cursor: pointer; z-index: 1; }
  .switch-fallback .track {
    position: absolute; inset: 0; border-radius: 7px;
    background-color: var(--switch-unchecked-track-color, #000); opacity: 0.38; transition: all 0.15s;
  }
  .switch-fallback .thumb {
    position: absolute; top: -3px; left: -2px; width: 20px; height: 20px; border-radius: 50%;
    background-color: var(--switch-unchecked-button-color, #fafafa);
    box-shadow: 0 2px 1px -1px rgba(0,0,0,.2), 0 1px 1px 0 rgba(0,0,0,.14), 0 1px 3px 0 rgba(0,0,0,.12);
    transition: all 0.15s;
  }
  .switch-fallback input:checked ~ .track { background-color: var(--switch-checked-track-color, var(--primary-color)); opacity: 0.54; }
  .switch-fallback input:checked ~ .thumb { left: 18px; background-color: var(--switch-checked-button-color, var(--primary-color)); }
  .fab {
    position: fixed;
    right: calc(16px + env(safe-area-inset-right, 0px));
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    z-index: 3;
    display: inline-flex;
    align-items: center;
    height: 48px;
    padding: 0 var(--ha-space-4, 16px) 0 var(--ha-space-2, 8px);
    border: none;
    border-radius: var(--ha-border-radius-pill, 9999px);
    cursor: pointer;
    background-color: var(--ha-color-fill-primary-loud-resting, var(--primary-color));
    color: var(--ha-color-on-primary-loud, var(--text-primary-color, white));
    font-family: inherit;
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: 1;
    white-space: nowrap;
    -webkit-tap-highlight-color: transparent;
    box-shadow: var(--ha-box-shadow-l, 0 6px 12px -3px rgba(0, 0, 0, 0.12), 0 16px 32px -6px rgba(0, 0, 0, 0.2));
    transition: background-color var(--ha-animation-duration-fast, 150ms) ease-out;
  }
  :host(:not([narrow])) .fab {
    right: calc(24px + env(safe-area-inset-right, 0px));
    bottom: calc(24px + env(safe-area-inset-bottom, 0px));
  }
  .fab svg { width: 24px; height: 24px; fill: currentColor; margin-inline-end: var(--ha-space-1, 4px); }
  .fab-label { padding: var(--ha-space-1, 4px) 0; }
  @media (hover: hover) {
    .fab:hover { background-color: var(--ha-color-fill-primary-loud-hover, var(--dark-primary-color, #0288d1)); }
  }
  .fab:active { background-color: var(--ha-color-fill-primary-loud-active, var(--primary-color)); }
  .fab:focus-visible { outline: 3px solid var(--ha-color-focus, var(--primary-color)); outline-offset: 2px; }
  .scrim {
    position: fixed; inset: 0; z-index: 10;
    background-color: var(--mdc-dialog-scrim-color, rgba(0, 0, 0, 0.32));
    display: flex; align-items: center; justify-content: center;
    padding: 24px; box-sizing: border-box;
    --show-duration: var(--ha-dialog-show-duration, 200ms);
    --hide-duration: var(--ha-dialog-hide-duration, 200ms);
    animation: show-backdrop var(--show-duration) ease;
  }
  .scrim.closing {
    pointer-events: none;
    animation: hide-backdrop var(--hide-duration) cubic-bezier(0.75, 0, 0.75, 0.9) forwards;
  }
  .scrim .dialog { animation: show-dialog var(--show-duration) ease; }
  .scrim.closing .dialog { animation: hide-dialog var(--hide-duration) cubic-bezier(0.75, 0, 0.75, 0.9) forwards; }
  @keyframes show-backdrop { from { background-color: transparent; } }
  @keyframes hide-backdrop { to { background-color: transparent; } }
  @keyframes show-dialog { from { opacity: 0; scale: 0.8; } }
  @keyframes hide-dialog { to { opacity: 0; scale: 0.8; } }
  @media (prefers-reduced-motion: reduce) {
    .scrim { --show-duration: 0ms; --hide-duration: 0ms; }
  }
  .dialog {
    background-color: var(--ha-dialog-surface-background, var(--mdc-theme-surface, var(--card-background-color, white)));
    color: var(--primary-text-color);
    border-radius: var(--ha-dialog-border-radius, var(--ha-border-radius-3xl, 24px));
    width: 100%;
    max-width: 480px;
    max-height: calc(100vh - 48px);
    display: flex;
    flex-direction: column;
    box-shadow: var(--dialog-box-shadow, 4px 8px 12px 0 rgba(0, 0, 0, 0.3));
  }
  .dialog-header {
    display: flex; align-items: center;
    padding: 0 var(--ha-space-1, 4px);
  }
  @media all and (min-width: 450px) and (min-height: 500px) {
    .dialog-header { padding: 0 var(--ha-space-2, 8px); }
  }
  .dialog-title {
    flex: 1; min-width: 0;
    padding: 10px var(--ha-space-1, 4px);
    min-height: var(--ha-space-12, 48px);
    display: flex; align-items: center;
    font-size: var(--ha-font-size-xl, 20px);
    line-height: var(--ha-line-height-condensed, 1.2);
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--ha-dialog-header-title-color, var(--primary-text-color));
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .icon-btn {
    position: relative; flex: none;
    display: inline-flex; align-items: center; justify-content: center;
    width: 48px; height: 48px; padding: 0;
    border: none; border-radius: 50%; background: none;
    color: inherit; cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .icon-btn svg { width: 24px; height: 24px; fill: currentColor; }
  .icon-btn::after {
    content: ""; position: absolute; inset: 0; border-radius: 50%;
    background-color: currentColor; opacity: 0; pointer-events: none;
  }
  @media (hover: hover) {
    .icon-btn:hover::after { opacity: 0.1; }
  }
  .icon-btn:focus-visible { outline: 3px solid var(--ha-color-focus, var(--primary-color)); outline-offset: -4px; }
  .dialog-body { padding: 0 var(--ha-space-6, 24px) var(--ha-space-6, 24px); overflow-y: auto; }
  .dialog-actions {
    display: flex; align-items: center; gap: var(--ha-space-3, 12px);
    padding: var(--ha-space-3, 12px) var(--ha-space-4, 16px) var(--ha-space-4, 16px);
  }
  .dialog-actions .spacer { flex: 1; }
  .field {
    position: relative;
    background-color: var(--ha-color-form-background, var(--mdc-text-field-fill-color, whitesmoke));
    border-radius: var(--ha-border-radius-sm, 4px) var(--ha-border-radius-sm, 4px) 0 0;
    margin-bottom: 20px;
    transition: background-color var(--ha-animation-duration-fast, 150ms) ease-in-out;
  }
  .field:hover { background-color: var(--ha-color-form-background-hover, var(--mdc-text-field-hover-fill-color, #e6e6e6)); }
  .field::before {
    content: ""; position: absolute; left: 0; right: 0; bottom: 0;
    height: 1px; pointer-events: none;
    background-color: var(--ha-color-border-neutral-loud, var(--mdc-text-field-idle-line-color, rgba(0, 0, 0, 0.42)));
    transition:
      height var(--ha-animation-duration-fast, 150ms) ease-in-out,
      background-color var(--ha-animation-duration-fast, 150ms) ease-in-out;
  }
  .field:focus-within::before, .field.select.open::before { height: 2px; background-color: var(--primary-color); }
  .field label {
    position: absolute; left: 16px; top: 8px;
    font-size: 12px; line-height: 16px;
    color: var(--secondary-text-color);
    pointer-events: none;
    transition: color var(--ha-animation-duration-fast, 150ms) ease-in-out;
  }
  .field:focus-within label, .field.select.open label { color: var(--primary-color); }
  .field input, .field .select-value {
    display: block; width: 100%; box-sizing: border-box;
    border: none; outline: none; background: none;
    color: var(--primary-text-color);
    font-family: inherit; font-size: var(--ha-font-size-l, 16px);
    padding: 26px 16px 8px; appearance: none; -webkit-appearance: none;
  }
  .field input[type="time"] { font-size: 28px; padding-top: 28px; font-variant-numeric: tabular-nums; }
  .field.select { cursor: pointer; outline: none; --ha-ripple-color: var(--primary-text-color); }
  .field.select:hover { background-color: var(--ha-color-form-background, var(--mdc-text-field-fill-color, whitesmoke)); }
  .field .select-value { padding-right: 40px; line-height: 24px; min-height: 58px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .menu {
    position: absolute; z-index: 11;
    display: flex; flex-direction: column;
    box-sizing: border-box; padding: 4px;
    overflow-y: auto; overscroll-behavior: contain;
    background-color: var(--card-background-color, var(--ha-dialog-surface-background, var(--mdc-theme-surface, #fff)));
    color: var(--primary-text-color);
    border: 1px solid var(--ha-color-border-neutral-quiet, var(--divider-color, rgba(0, 0, 0, 0.12)));
    border-radius: var(--ha-border-radius-md, 8px);
    box-shadow: var(--ha-box-shadow-m, 0 3px 6px -1px rgba(0, 0, 0, 0.1), 0 8px 16px -2px rgba(0, 0, 0, 0.15));
    font-size: var(--ha-font-size-m, 14px);
    user-select: none;
    --show-duration: var(--ha-animation-duration-instant, 75ms);
    --hide-duration: var(--ha-animation-duration-instant, 75ms);
    animation: show-menu var(--show-duration) ease;
  }
  .menu.closing { pointer-events: none; animation: hide-menu var(--hide-duration) ease forwards; }
  @keyframes show-menu { from { opacity: 0; scale: 0.9; } }
  @keyframes hide-menu { to { opacity: 0; scale: 0.9; } }
  @media (prefers-reduced-motion: reduce) {
    .menu { --show-duration: 0ms; --hide-duration: 0ms; }
  }
  .menu-item {
    display: flex; align-items: center; flex: none;
    min-height: 40px; padding: 0 1em;
    border-radius: var(--ha-border-radius-sm, 4px);
    cursor: pointer;
    transition:
      background-color var(--ha-animation-duration-instant, 75ms) ease,
      color var(--ha-animation-duration-instant, 75ms) ease;
  }
  .menu-item:hover, .menu-item.active {
    background-color: var(--ha-color-fill-neutral-normal-resting, rgba(var(--rgb-primary-text-color, 33, 33, 33), 0.08));
  }
  .menu-item.selected {
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--primary-color);
    background-color: var(--ha-color-fill-primary-quiet-resting, rgba(var(--rgb-primary-color, 3, 169, 244), 0.12));
  }
  .menu-item.selected:hover, .menu-item.selected.active {
    background-color: var(--ha-color-fill-primary-quiet-hover, rgba(var(--rgb-primary-color, 3, 169, 244), 0.18));
  }
  .field.select::after {
    content: ""; position: absolute; right: 16px; top: 50%; margin-top: 2px;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 5px solid var(--secondary-text-color); pointer-events: none;
  }
  .section-label {
    font-size: var(--ha-font-size-m, 14px);
    color: var(--secondary-text-color);
    margin: 4px 0 8px;
  }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
  .chip {
    display: inline-flex; align-items: center; gap: 8px;
    height: 32px; padding: 0 16px; box-sizing: border-box;
    border-radius: 8px;
    border: 1px solid var(--outline-color, var(--divider-color, #79747e));
    background: none; color: var(--primary-text-color);
    font-family: inherit; font-size: var(--ha-font-size-m, 14px); font-weight: var(--ha-font-weight-medium, 500);
    cursor: pointer;
  }
  .chip.selected {
    border-color: transparent;
    background-color: rgba(var(--rgb-primary-color, 3, 169, 244), 0.15);
    color: var(--primary-color);
  }
  .days { flex-wrap: nowrap; gap: 6px; }
  .days .chip { flex: 1; min-width: 0; padding: 0; justify-content: center; }
  .presets {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-bottom: 20px;
  }
  .presets.two-col { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .presets .chip { justify-content: center; padding: 0 8px; white-space: nowrap; overflow: hidden; }
  .settings-row {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    min-height: 48px; margin-bottom: 8px;
    font-size: var(--ha-font-size-l, 16px);
  }
  .btn {
    display: inline-flex; align-items: center; justify-content: center;
    border: none; cursor: pointer;
    font-family: inherit; font-size: var(--ha-font-size-m, 14px); font-weight: var(--ha-font-weight-medium, 500);
    line-height: 1; white-space: nowrap;
    height: 40px; padding: 0 var(--ha-space-4, 16px);
    border-radius: var(--ha-border-radius-pill, 9999px);
    -webkit-tap-highlight-color: transparent;
    transition: background-color var(--ha-animation-duration-fast, 150ms) ease-out;
  }
  .btn.filled {
    background-color: var(--ha-color-fill-primary-loud-resting, var(--primary-color));
    color: var(--ha-color-on-primary-loud, var(--text-primary-color, white));
  }
  .btn.danger {
    background-color: transparent;
    color: var(--ha-color-on-danger-normal, var(--error-color, #db4437));
  }
  .btn.danger.armed {
    background-color: var(--ha-color-fill-danger-loud-resting, var(--error-color, #db4437));
    color: var(--ha-color-on-danger-loud, white);
  }
  @media (hover: hover) {
    .btn.filled:not(:disabled):hover { background-color: var(--ha-color-fill-primary-loud-hover, var(--dark-primary-color, #0288d1)); }
    .btn.danger:not(:disabled):hover { background-color: var(--ha-color-fill-danger-quiet-hover, rgba(219, 68, 55, 0.12)); }
    .btn.danger.armed:not(:disabled):hover { background-color: var(--ha-color-fill-danger-loud-hover, #b30532); }
  }
  .btn.filled:not(:disabled):active { background-color: var(--ha-color-fill-primary-loud-active, var(--primary-color)); }
  .btn.danger:not(:disabled):active { background-color: var(--ha-color-fill-danger-quiet-active, rgba(219, 68, 55, 0.08)); }
  .btn.danger.armed:not(:disabled):active { background-color: var(--ha-color-fill-danger-loud-active, var(--error-color, #db4437)); }
  .btn:focus-visible { outline: 3px solid var(--ha-color-focus, var(--primary-color)); outline-offset: 2px; }
  .btn:disabled { opacity: 0.38; cursor: default; }
  .error { color: var(--error-color, #db4437); font-size: var(--ha-font-size-m, 14px); margin-bottom: 8px; }
`;

class QingpingAlarmsPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._narrow = false;
    this._dialog = null;
    this._built = false;
    this._lastSignature = "";
    this._lastStructure = "";
    this._devices = null;
    this._unsub = null;
    this._haReady = false;
    this._lang = null;
    this._texts = null;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (!this._built) this._build();
    if (this._menuButton) this._menuButton.hass = hass;
    if (hass.themes?.darkMode !== undefined) this.style.colorScheme = hass.themes.darkMode ? "dark" : "light";
    if (first) this._loadHaElements();
    if (hass.language !== this._lang) this._loadTexts();
    this._subscribe();
    this._renderList();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    if (this._menuButton) this._menuButton.narrow = narrow;
    this.shadowRoot.querySelector(".toolbar")?.classList.toggle("narrow", !!narrow);
    this.toggleAttribute("narrow", !!narrow);
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    if (this._hass) this._subscribe();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
  }

  get _t() {
    return this._texts;
  }

  async _loadTexts() {
    const lang = this._hass.language;
    this._lang = lang;
    let localize = null;
    try {
      localize = await this._hass.loadBackendTranslation("selector", DOMAIN);
    } catch (err) {
      localize = this._hass.localize;
    }
    if (lang !== this._lang) return;
    const texts = {};
    for (const key of TEXT_KEYS) {
      texts[key] = localize?.(`component.${DOMAIN}.selector.panel.options.${key}`) || key;
    }
    const format = new Intl.DateTimeFormat(this._hass.locale?.language || lang, { weekday: "short", timeZone: "UTC" });
    texts.days = Object.fromEntries(
      WEEKDAYS.map((day, i) => {
        const name = format.format(new Date(Date.UTC(2024, 0, 1 + i)));
        return [day, name.charAt(0).toUpperCase() + name.slice(1)];
      })
    );
    this._texts = texts;
    this._lastSignature = "";
    this._lastStructure = "";
    this._renderList();
  }

  async _loadHaElements() {
    if (window.loadCardHelpers) await window.loadCardHelpers().catch(() => {});
    this._haReady = true;
    this._lastSignature = "";
    this._lastStructure = "";
    this._renderList();
  }

  _subscribe() {
    if (this._unsub || !this._hass?.connection) return;
    this._unsub = this._hass.connection.subscribeMessage(
      (msg) => {
        this._devices = msg.devices;
        this._renderList();
      },
      { type: `${DOMAIN}/alarms/subscribe` }
    );
    this._unsub.catch(() => {
      this._unsub = null;
    });
  }

  _daysLabel(days) {
    const t = this._t;
    const preset = PRESETS.find(([, presetDays]) => sameDays(presetDays, days));
    if (preset) return t[preset[0]];
    return WEEKDAYS.filter((d) => days.includes(d)).map((d) => t.days[d]).join(", ");
  }

  _build() {
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <div class="toolbar ${this._narrow ? "narrow" : ""}">
        <span class="menu-slot"></span>
        <div class="main-title"></div>
      </div>
      <div class="content"></div>
      <button class="fab" hidden>${svgIcon(ICONS.plus)}<span class="fab-label"></span></button>
      <div class="dialog-host"></div>
    `;
    const root = this.shadowRoot;
    const slot = root.querySelector(".menu-slot");
    if (customElements.get("ha-menu-button")) {
      this._menuButton = document.createElement("ha-menu-button");
      this._menuButton.hass = this._hass;
      this._menuButton.narrow = this._narrow;
      slot.appendChild(this._menuButton);
    } else {
      slot.innerHTML = `<button class="fallback-menu" title="Menu">${svgIcon(ICONS.menu)}</button>`;
      slot.firstElementChild.addEventListener("click", () => {
        this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
      });
    }
    root.querySelector(".fab").addEventListener("click", () => this._openDialog(null));
    const content = root.querySelector(".content");
    content.addEventListener("click", (ev) => this._onListClick(ev));
    this._bindRipple(content, (path) =>
      path.some((el) => el.dataset?.toggle || el.classList?.contains("switch-fallback"))
        ? null
        : path.find((el) => el.classList?.contains("row"))
    );
  }

  _bindRipple(container, findTarget) {
    container.addEventListener("pointerdown", (ev) => this._onRippleDown(ev, findTarget));
    container.addEventListener("pointerup", () => this._endRipple(true));
    container.addEventListener("pointercancel", () => this._endRipple(false));
    container.addEventListener("pointerout", (ev) => {
      if (this._ripple && !this._ripple.target.contains(ev.relatedTarget)) this._endRipple(false);
    });
    container.addEventListener("contextmenu", () => this._endRipple(false));
  }

  _onRippleDown(ev, findTarget) {
    if (!ev.isPrimary || (ev.pointerType === "mouse" && ev.button !== 0)) return;
    const target = findTarget(ev.composedPath());
    if (!target) return;
    this._endRipple(false);
    const rect = target.getBoundingClientRect();
    const point = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
    this._ripple = { target, point };
    if (ev.pointerType === "touch") {
      this._ripple.timer = setTimeout(() => this._startRipple(), 150);
    } else {
      this._startRipple();
    }
  }

  _startRipple() {
    const ripple = this._ripple;
    if (!ripple || ripple.animation) return;
    clearTimeout(ripple.timer);
    ripple.timer = null;
    const { target, point } = ripple;
    const { width, height } = target.getBoundingClientRect();
    const maxDim = Math.max(width, height);
    const softEdge = Math.max(0.35 * maxDim, 75);
    const size = Math.floor(maxDim * 0.2);
    const scale = (Math.hypot(width, height) + 10 + softEdge) / size;
    const press = target.querySelector(":scope > .ripple .press");
    press.style.width = press.style.height = `${size}px`;
    target.classList.add("pressed");
    ripple.animation = press.animate(
      [
        { transform: `translate(${point.x - size / 2}px, ${point.y - size / 2}px) scale(1)` },
        { transform: `translate(${(width - size) / 2}px, ${(height - size) / 2}px) scale(${scale})` },
      ],
      { duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 450, easing: "cubic-bezier(0.2, 0, 0, 1)", fill: "forwards" }
    );
  }

  async _endRipple(released) {
    const ripple = this._ripple;
    if (!ripple) return;
    this._ripple = null;
    if (ripple.timer) {
      clearTimeout(ripple.timer);
      if (!released) return;
      this._ripple = ripple;
      this._startRipple();
      this._ripple = null;
    }
    const elapsed = Number(ripple.animation?.currentTime ?? Infinity);
    if (elapsed < 225) await new Promise((resolve) => setTimeout(resolve, 225 - elapsed));
    if (this._ripple?.target === ripple.target) return;
    ripple.target.classList.remove("pressed");
  }

  _switchHtml(checked, attrs) {
    if (customElements.get("ha-switch")) {
      return `<ha-switch ${attrs} ${checked ? "checked" : ""}></ha-switch>`;
    }
    return `<span class="switch-fallback"><input type="checkbox" ${attrs} ${checked ? "checked" : ""}><span class="track"></span><span class="thumb"></span></span>`;
  }

  _renderList() {
    if (!this._built || !this._haReady || !this._texts) return;
    const t = this._t;
    const devices = (this._devices || []).map((dev) => ({
      id: dev.device_id,
      name: dev.name,
      alarms: dev.alarms.map((alarm) => ({ ...alarm, key: `${dev.device_id}:${alarm.id}` })),
    }));
    this._deviceList = devices;
    const signature = JSON.stringify([this._hass.language, devices]);
    if (signature === this._lastSignature) return;
    this._lastSignature = signature;

    const root = this.shadowRoot;
    root.querySelector(".main-title").textContent = t.title;
    const fab = root.querySelector(".fab");
    fab.hidden = devices.length === 0;
    fab.querySelector(".fab-label").textContent = t.add;

    const structure = JSON.stringify([
      this._hass.language,
      this._devices === null,
      devices.map((dev) => [dev.id, dev.name, dev.alarms.map((alarm) => alarm.key)]),
    ]);
    if (structure === this._lastStructure) {
      this._updateRows(devices);
      return;
    }
    this._lastStructure = structure;

    let html = "";
    if (!devices.length && this._devices !== null) {
      html = `<ha-card><div class="card-header">${escapeHtml(t.title)}</div><div class="empty">${escapeHtml(t.no_devices)}</div></ha-card>`;
    }
    for (const device of devices) {
      html += `<ha-card><div class="card-header">${escapeHtml(device.name)}</div><div class="card-content">`;
      if (!device.alarms.length) html += `<div class="empty">${escapeHtml(t.empty)}</div>`;
      for (const alarm of device.alarms) {
        html += `
          <div class="row" data-key="${escapeHtml(alarm.key)}">
            <span class="ripple"><span class="press"></span></span>
            <div class="icon"></div>
            <div class="info">
              <div class="primary"></div>
              <div class="secondary"></div>
            </div>
            ${this._switchHtml(alarm.enabled, `data-toggle="${escapeHtml(alarm.key)}"`)}
          </div>`;
      }
      html += `</div></ha-card>`;
    }
    const content = root.querySelector(".content");
    content.innerHTML = html;
    content.querySelectorAll("[data-toggle]").forEach((toggle) => {
      toggle.addEventListener("change", () => this._onToggle(toggle));
    });
    this._updateRows(devices);
  }

  _updateRows(devices) {
    const rows = new Map([...this.shadowRoot.querySelectorAll(".content .row")].map((row) => [row.dataset.key, row]));
    for (const device of devices) {
      for (const alarm of device.alarms) {
        const row = rows.get(alarm.key);
        if (!row) continue;
        row.classList.toggle("on", alarm.enabled);
        const icon = alarm.enabled ? "alarm" : "alarmOff";
        if (row.dataset.icon !== icon) {
          row.dataset.icon = icon;
          row.querySelector(".icon").innerHTML = svgIcon(ICONS[icon]);
        }
        row.querySelector(".primary").textContent = alarm.time;
        row.querySelector(".secondary").textContent = [this._daysLabel(alarm.days), alarm.ringtone].join(" · ");
        const toggle = row.querySelector("[data-toggle]");
        if (toggle.checked !== alarm.enabled) toggle.checked = alarm.enabled;
      }
    }
  }

  _findAlarm(key) {
    for (const device of this._deviceList || []) {
      const alarm = device.alarms.find((a) => a.key === key);
      if (alarm) return { device, alarm };
    }
    return null;
  }

  _onListClick(ev) {
    const path = ev.composedPath();
    if (path.some((el) => el.dataset?.toggle || el.classList?.contains("switch-fallback"))) return;
    const row = path.find((el) => el.classList?.contains("row"));
    if (!row) return;
    const found = this._findAlarm(row.dataset.key);
    if (found) this._openDialog(found.alarm, found.device);
  }

  async _onToggle(toggle) {
    const found = this._findAlarm(toggle.dataset.toggle);
    if (!found) return;
    try {
      await this._hass.callService(DOMAIN, "update_alarm", {
        device_id: found.device.id,
        alarm_id: found.alarm.id,
        enabled: toggle.checked,
      });
    } catch (err) {
      toggle.checked = !toggle.checked;
    }
  }

  _openDialog(alarm, device) {
    const t = this._t;
    const devices = this._deviceList || [];
    this._dialog = {
      alarmId: alarm ? alarm.id : null,
      deviceId: device?.id || devices[0]?.id,
      time: alarm?.time || "07:00",
      days: [...(alarm?.days || [])],
      ringtone: alarm?.ringtone || DEFAULT_RINGTONE,
      snooze: alarm ? alarm.snooze : false,
      deleteArmed: false,
    };
    const d = this._dialog;
    const ringtones = RINGTONES.includes(d.ringtone) ? RINGTONES : [...RINGTONES, d.ringtone];
    const closeLabel = this._hass.localize?.("ui.common.close") || "Close";
    const host = this.shadowRoot.querySelector(".dialog-host");
    host.innerHTML = `
      <div class="scrim">
        <div class="dialog" role="dialog" aria-modal="true">
          <div class="dialog-header">
            <button class="icon-btn close" title="${escapeHtml(closeLabel)}" aria-label="${escapeHtml(closeLabel)}">${svgIcon(ICONS.close)}</button>
            <div class="dialog-title">${escapeHtml(d.alarmId !== null ? t.edit : t.add)}</div>
          </div>
          <div class="dialog-body">
            ${d.alarmId === null && devices.length > 1 ? this._selectHtml("device", t.device) : ""}
            <div class="field">
              <label>${escapeHtml(t.time)}</label>
              <input type="time" class="time-input" step="60" value="${escapeHtml(d.time)}">
            </div>
            <div class="section-label">${escapeHtml(t.repeat)}</div>
            <div class="chips days"></div>
            <div class="chips presets"></div>
            ${this._selectHtml("ringtone", t.ringtone)}
            <div class="settings-row">
              <span>${escapeHtml(t.snooze)}</span>
              ${this._switchHtml(d.snooze, 'class="snooze"')}
            </div>
            <div class="error" hidden></div>
          </div>
          <div class="dialog-actions">
            ${d.alarmId !== null ? `<button class="btn danger delete">${escapeHtml(t.delete)}</button>` : ""}
            <span class="spacer"></span>
            <button class="btn filled save">${escapeHtml(t.save)}</button>
          </div>
        </div>
      </div>`;
    const q = (sel) => host.querySelector(sel);
    this._renderDayChips();
    q(".scrim").addEventListener("click", (ev) => {
      if (ev.target === ev.currentTarget) this._closeDialog();
    });
    q(".close").addEventListener("click", () => this._closeDialog());
    q(".save").addEventListener("click", () => this._save());
    q(".delete")?.addEventListener("click", () => this._delete());
    q(".time-input").addEventListener("input", (ev) => (d.time = ev.target.value));
    this._bindSelect(q(".ringtone"), ringtones.map((r) => ({ value: r, label: r })), d.ringtone, (value) => (d.ringtone = value));
    q(".snooze").addEventListener("change", (ev) => (d.snooze = ev.target.checked));
    if (q(".device")) {
      this._bindSelect(q(".device"), devices.map((dev) => ({ value: dev.id, label: dev.name })), d.deviceId, (value) => (d.deviceId = value));
    }
    this._keyHandler = (ev) => {
      if (ev.key !== "Escape") return;
      if (this._menu) this._closeMenu();
      else this._closeDialog();
    };
    window.addEventListener("keydown", this._keyHandler);
    this._resizeObserver = new ResizeObserver(() => this._fitPresets());
    this._resizeObserver.observe(q(".dialog-body"));
  }

  _selectHtml(cls, label) {
    return `
      <div class="field select ${cls}" tabindex="0" role="combobox" aria-haspopup="listbox" aria-expanded="false">
        <span class="ripple"><span class="press"></span></span>
        <label>${escapeHtml(label)}</label>
        <div class="select-value"></div>
      </div>`;
  }

  _bindSelect(field, options, value, onChange) {
    const select = { field, options, value, onChange };
    const show = () => (field.querySelector(".select-value").textContent = options.find((o) => o.value === select.value)?.label ?? "");
    select.set = (newValue) => {
      select.value = newValue;
      show();
      onChange(newValue);
    };
    show();
    this._bindRipple(field, () => field);
    field.addEventListener("click", () => (this._menu?.select === select ? this._closeMenu() : this._openMenu(select)));
    field.addEventListener("keydown", (ev) => this._onSelectKey(ev, select));
  }

  _openMenu(select) {
    this._closeMenu(true);
    const { field, options } = select;
    const scrim = field.closest(".scrim");
    const rect = field.getBoundingClientRect();
    const scrimRect = scrim.getBoundingClientRect();
    const menu = document.createElement("div");
    menu.className = "menu";
    menu.setAttribute("role", "listbox");
    menu.innerHTML = options
      .map((o, i) => `<div class="menu-item ${o.value === select.value ? "selected" : ""}" role="option" data-index="${i}">${escapeHtml(o.label)}</div>`)
      .join("");
    const below = window.innerHeight - rect.bottom - 8;
    const above = rect.top - 8;
    menu.style.left = `${rect.left - scrimRect.left}px`;
    menu.style.width = `${rect.width}px`;
    if (below >= Math.min(320, above)) {
      menu.style.top = `${rect.bottom - scrimRect.top}px`;
      menu.style.maxHeight = `${below}px`;
      menu.style.transformOrigin = "top";
    } else {
      menu.style.bottom = `${scrimRect.bottom - rect.top}px`;
      menu.style.maxHeight = `${above}px`;
      menu.style.transformOrigin = "bottom";
    }
    menu.addEventListener("click", (ev) => {
      const item = ev.target.closest(".menu-item");
      if (!item) return;
      select.set(options[Number(item.dataset.index)].value);
      this._closeMenu();
      field.focus();
    });
    menu.addEventListener("mousedown", (ev) => ev.preventDefault());
    scrim.appendChild(menu);
    menu.querySelector(".selected")?.scrollIntoView({ block: "nearest" });
    field.classList.add("open");
    field.setAttribute("aria-expanded", "true");
    this._menu = { menu, select, active: options.findIndex((o) => o.value === select.value) };
    this._menuOutside = (ev) => {
      const path = ev.composedPath();
      if (path.includes(menu) || path.includes(field)) return;
      this._closeMenu();
      this.shadowRoot.addEventListener(
        "click",
        (click) => {
          if (click.target.classList?.contains("scrim")) click.stopPropagation();
        },
        { capture: true, once: true }
      );
    };
    this.shadowRoot.addEventListener("pointerdown", this._menuOutside, true);
    this._menuScroll = (ev) => {
      if (!ev.composedPath().includes(menu)) this._closeMenu();
    };
    field.closest(".dialog-body").addEventListener("scroll", this._menuScroll);
    window.addEventListener("resize", this._menuScroll);
  }

  _closeMenu(immediate = false) {
    if (!this._menu) return;
    const { menu, select } = this._menu;
    this._menu = null;
    this.shadowRoot.removeEventListener("pointerdown", this._menuOutside, true);
    select.field.closest(".dialog-body")?.removeEventListener("scroll", this._menuScroll);
    window.removeEventListener("resize", this._menuScroll);
    select.field.classList.remove("open");
    select.field.setAttribute("aria-expanded", "false");
    if (immediate || matchMedia("(prefers-reduced-motion: reduce)").matches) {
      menu.remove();
      return;
    }
    menu.classList.add("closing");
    menu.addEventListener("animationend", () => menu.remove(), { once: true });
  }

  _onSelectKey(ev, select) {
    const open = this._menu?.select === select;
    if (!open) {
      if (["Enter", " ", "ArrowDown", "ArrowUp"].includes(ev.key)) {
        ev.preventDefault();
        this._openMenu(select);
      }
      return;
    }
    const items = this._menu.menu.querySelectorAll(".menu-item");
    if (ev.key === "Escape" || ev.key === "Tab") {
      if (ev.key === "Escape") {
        ev.preventDefault();
        ev.stopPropagation();
      }
      this._closeMenu();
    } else if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
      ev.preventDefault();
      const step = ev.key === "ArrowDown" ? 1 : -1;
      this._menu.active = Math.min(items.length - 1, Math.max(0, this._menu.active + step));
      items.forEach((item, i) => item.classList.toggle("active", i === this._menu.active));
      items[this._menu.active].scrollIntoView({ block: "nearest" });
    } else if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      if (this._menu.active >= 0) select.set(select.options[this._menu.active].value);
      this._closeMenu();
    }
  }

  _chipHtml(label, selected, attrs) {
    return `<button class="chip ${selected ? "selected" : ""}" ${attrs}>${escapeHtml(label)}</button>`;
  }

  _renderDayChips() {
    const t = this._t;
    const d = this._dialog;
    const host = this.shadowRoot.querySelector(".dialog-host");
    const days = host.querySelector(".days");
    days.innerHTML = WEEKDAYS.map((day) => this._chipHtml(t.days[day], d.days.includes(day), `data-day="${day}"`)).join("");
    days.querySelectorAll(".chip").forEach((chip) =>
      chip.addEventListener("click", () => {
        const day = chip.dataset.day;
        d.days = d.days.includes(day) ? d.days.filter((x) => x !== day) : [...d.days, day];
        this._renderDayChips();
      })
    );
    const presets = host.querySelector(".presets");
    presets.innerHTML = PRESETS.map(([key, presetDays]) =>
      this._chipHtml(t[key], sameDays(presetDays, d.days), `data-preset="${key}"`)
    ).join("");
    presets.querySelectorAll(".chip").forEach((chip) =>
      chip.addEventListener("click", () => {
        d.days = [...PRESETS.find(([key]) => key === chip.dataset.preset)[1]];
        this._renderDayChips();
      })
    );
    this._fitPresets();
  }

  _fitPresets() {
    const presets = this.shadowRoot.querySelector(".dialog-host .presets");
    if (!presets) return;
    presets.classList.remove("two-col");
    const overflows = [...presets.children].some((chip) => chip.scrollWidth > chip.clientWidth);
    presets.classList.toggle("two-col", overflows);
  }

  _closeDialog() {
    this._dialog = null;
    this._closeMenu();
    this._resizeObserver?.disconnect();
    window.removeEventListener("keydown", this._keyHandler);
    const scrim = this.shadowRoot.querySelector(".dialog-host .scrim");
    if (!scrim || matchMedia("(prefers-reduced-motion: reduce)").matches) {
      scrim?.remove();
      return;
    }
    scrim.classList.add("closing");
    scrim.querySelector(".dialog").addEventListener("animationend", () => scrim.remove(), { once: true });
  }

  _setBusy(busy, message) {
    const host = this.shadowRoot.querySelector(".dialog-host");
    host.querySelectorAll(".btn").forEach((b) => (b.disabled = busy));
    const error = host.querySelector(".error");
    if (error) {
      error.hidden = !message;
      error.textContent = message || "";
    }
  }

  async _call(service, data) {
    this._setBusy(true);
    try {
      await this._hass.callService(DOMAIN, service, data);
      this._closeDialog();
    } catch (err) {
      this._setBusy(false, `${this._t.error}: ${err?.message || err}`);
    }
  }

  _save() {
    const d = this._dialog;
    if (!d || !d.time) return;
    const data = {
      time: d.time.length === 5 ? `${d.time}:00` : d.time,
      days: WEEKDAYS.filter((day) => d.days.includes(day)),
      ringtone: d.ringtone,
      snooze: d.snooze,
    };
    if (d.alarmId !== null) {
      this._call("update_alarm", { device_id: d.deviceId, alarm_id: d.alarmId, ...data });
    } else {
      this._call("add_alarm", { device_id: d.deviceId, enabled: true, ...data });
    }
  }

  _delete() {
    const d = this._dialog;
    if (!d || d.alarmId === null) return;
    const btn = this.shadowRoot.querySelector(".dialog-host .delete");
    if (!d.deleteArmed) {
      d.deleteArmed = true;
      btn.classList.add("armed");
      btn.textContent = this._t.confirm_delete;
      return;
    }
    this._call("delete_alarm", { device_id: d.deviceId, alarm_id: d.alarmId });
  }
}

if (!customElements.get("qingping-alarms-panel")) {
  customElements.define("qingping-alarms-panel", QingpingAlarmsPanel);
}
