import { useState, useEffect } from "react";
import { Icon, Micro, Action } from "./Icon";

interface HeaderProps {
  theme: "government" | "navy" | "coastal";
  onThemeChange: (theme: "government" | "navy" | "coastal") => void;
}

export function Header({ theme, onThemeChange }: HeaderProps) {
  const [themeOpen, setThemeOpen] = useState(false);
  const [time, setTime] = useState("");

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false }) + " IST");
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="national-stripe" />
      <div className="government-bar">
        <span>भारत सरकार&nbsp;&nbsp;|&nbsp;&nbsp;Government of India</span>
        <span>Maritime Pollution Response</span>
      </div>
      <header className="command-header">
        <div className="brand-lockup">
          <div className="brand-mark"><Icon name="anchor" className="size-6" /><span className="brand-pulse" /></div>
          <div><p className="font-display text-base font-semibold tracking-wide">VARUNA</p><Micro className="text-fog">Ocean intelligence</Micro></div>
        </div>
        <div className="header-title">
          <Micro className="text-fog">Active case</Micro>
          <p className="mt-1 font-display text-sm">MUM-04 · Western Offshore</p>
        </div>
        <div className="header-meta">
          <span className="data-live">LIVE FUSION</span>
          <span className="hidden text-right sm:block"><Micro className="text-fog">Mumbai offshore</Micro><b className="block font-mono text-xs">{time}</b></span>
          <div className="theme-control">
            <Action className="theme-trigger" onClick={() => setThemeOpen((open) => !open)}>
              <Icon name="spark" className="size-4" />
              <span className="hidden sm:inline">Theme</span>
            </Action>
            {themeOpen && (
              <div className="theme-menu">
                <Micro className="text-fog">Colour theme</Micro>
                {[
                  ["government", "Government light", "theme-swatch-government"],
                  ["navy", "Navy command", "theme-swatch-navy"],
                  ["coastal", "Coastal neutral", "theme-swatch-coastal"],
                ].map(([value, label, swatch]) => (
                  <Action
                    key={value}
                    active={theme === value}
                    onClick={() => {
                      onThemeChange(value as "government" | "navy" | "coastal");
                      setThemeOpen(false);
                    }}
                    className="theme-option"
                  >
                    <span className={`theme-swatch ${swatch}`} />
                    <span>{label}</span>
                    {theme === value && <span className="theme-check">✓</span>}
                  </Action>
                ))}
              </div>
            )}
          </div>
          <Action className="size-11 border border-line"><Icon name="bell" className="size-4" /></Action>
        </div>
      </header>
    </>
  );
}
