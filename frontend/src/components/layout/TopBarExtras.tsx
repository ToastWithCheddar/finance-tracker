import { useEffect, useState } from 'react';
import { Bell, CheckCheck, Wifi, WifiOff, User, LogOut, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useConnectionStatus, useNotifications, useUnreadNotificationsCount } from '../../stores/realtimeStore';
import { useAuthStore, useAuthUser } from '../../stores/authStore';

export function ConnectionStatusChip() {
  const { status } = useConnectionStatus();
  const color = status === 'connected' ? 'bg-green-500' : status === 'connecting' ? 'bg-yellow-500' : 'bg-red-500';
  const Icon = status === 'connected' ? Wifi : WifiOff;
  const label = status.charAt(0).toUpperCase() + status.slice(1);
  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-border bg-[hsl(var(--surface))]">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <Icon className="h-4 w-4 opacity-80" />
      <span className="text-xs">{label}</span>
    </div>
  );
}

export function DateChip() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);
  const formatted = now.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
  return (
    <div className="px-3 py-1.5 rounded-md border border-border bg-[hsl(var(--surface))] text-sm">
      {formatted}
    </div>
  );
}

export function NotificationsBell() {
  const unread = useUnreadNotificationsCount();
  const notifications = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="relative p-2 rounded-full border border-border bg-[hsl(var(--surface))]">
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[10px] text-white grid place-items-center">{unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-md border border-border bg-[hsl(var(--surface))] shadow-lg z-50">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <div className="text-sm font-medium">Notifications</div>
            <button className="text-xs inline-flex items-center gap-1 opacity-80 hover:opacity-100"><CheckCheck className="h-3 w-3" /> Mark all read</button>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-[hsl(var(--text))/0.6] text-sm">No notifications</div>
            ) : notifications.slice(0, 8).map((n) => (
              <div key={n.id} className="px-3 py-2 border-b border-border text-sm">
                <div className="font-medium truncate">{n.title}</div>
                <div className="opacity-70 truncate">{n.message}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [imageError, setImageError] = useState(false);
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  const user = useAuthUser();

  const handleProfileClick = () => {
    setOpen(false);
    navigate('/profile');
  };

  const handleLogout = () => {
    setOpen(false);
    logout();
  };

  const getInitials = () => {
    if (user?.displayName) {
      return user.displayName.charAt(0).toUpperCase();
    }
    if (user?.email) {
      return user.email.charAt(0).toUpperCase();
    }
    return 'U';
  };

  const getDisplayName = () => {
    if (user?.displayName) return user.displayName;
    return 'User';
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (open && !(event.target as Element).closest('.profile-menu')) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  return (
    <div className="relative profile-menu">
      <button 
        onClick={() => setOpen(!open)} 
        className="flex items-center gap-2 px-2 py-1.5 rounded-md border border-border bg-[hsl(var(--surface))] hover:bg-[hsl(var(--border)/0.25)] transition-colors"
        title={`${getDisplayName()} - Click to open profile menu`}
      >
        <div className="w-6 h-6 rounded-full overflow-hidden bg-gradient-to-br from-[hsl(var(--brand))] to-blue-500 flex items-center justify-center text-white text-xs font-medium">
          {user?.avatarUrl && !imageError ? (
            <img
              src={user.avatarUrl}
              alt="Profile"
              className="w-full h-full object-cover"
              onError={() => setImageError(true)}
            />
          ) : (
            getInitials()
          )}
        </div>
        <ChevronDown className={`h-4 w-4 opacity-70 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-64 rounded-md border border-border bg-[hsl(var(--surface))] shadow-lg z-50">
          {/* User Info Header */}
          <div className="px-3 py-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full overflow-hidden bg-gradient-to-br from-[hsl(var(--brand))] to-blue-500 flex items-center justify-center text-white text-sm font-medium">
                {user?.avatarUrl && !imageError ? (
                  <img
                    src={user.avatarUrl}
                    alt="Profile"
                    className="w-full h-full object-cover"
                    onError={() => setImageError(true)}
                  />
                ) : (
                  getInitials()
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-[hsl(var(--text))] truncate">
                  {getDisplayName()}
                </div>
                <div className="text-xs text-[hsl(var(--text))] opacity-70 truncate">
                  {user?.email}
                </div>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-1">
            <button 
              onClick={handleProfileClick}
              className="w-full text-left px-3 py-2 text-sm hover:bg-[hsl(var(--border)/0.25)] inline-flex items-center gap-2 transition-colors"
            >
              <User className="h-4 w-4" /> 
              Profile & Settings
            </button>
          </div>
          
          <div className="border-t border-border" />
          
          <div className="py-1">
            <button 
              onClick={handleLogout} 
              className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-500/10 inline-flex items-center gap-2 transition-colors"
            >
              <LogOut className="h-4 w-4" /> 
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}


