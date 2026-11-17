import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle({ className = '' }) {
  const { theme, toggle } = useTheme();
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <button type="button" className={`theme-toggle ${className}`} onClick={toggle} aria-pressed={theme === 'dark'}>
      <span className="theme-mark" aria-hidden="true" />
      {next === 'dark' ? 'Dark mode' : 'Light mode'}
    </button>
  );
}
