import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function AppLayout() {
  return (
    <div className="shell">
      <Sidebar />
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
