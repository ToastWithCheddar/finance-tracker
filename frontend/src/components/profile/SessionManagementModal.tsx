import { useState, useEffect } from 'react';
import { Smartphone, Monitor, Globe, Trash2, Shield, AlertTriangle, Loader2, Calendar, MapPin } from 'lucide-react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { LoadingSpinner } from '../ui';
import { userService } from '../../services/userService';

interface SessionManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface UserSession {
  id: string;
  device: string;
  location: string;
  last_active: string;
  is_current: boolean;
}

export function SessionManagementModal({ isOpen, onClose }: SessionManagementModalProps) {
  const [sessions, setSessions] = useState<UserSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRevoking, setIsRevoking] = useState<string | null>(null);
  const [isRevokingAll, setIsRevokingAll] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load sessions when modal opens
  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen]);

  const loadSessions = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const sessionsData = await userService.getUserSessions();
      setSessions(sessionsData);
    } catch (error) {
      console.error('Failed to load sessions:', error);
      setError('Failed to load active sessions');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to revoke this session? The user will be logged out from that device.')) {
      return;
    }

    try {
      setIsRevoking(sessionId);
      await userService.revokeSession(sessionId);
      
      // Remove session from local state
      setSessions(prev => prev.filter(session => session.id !== sessionId));
      
      // Show success message
      alert('Session revoked successfully');
    } catch (error) {
      console.error('Failed to revoke session:', error);
      alert('Failed to revoke session. Please try again.');
    } finally {
      setIsRevoking(null);
    }
  };

  const handleRevokeAllSessions = async () => {
    const confirmMessage = 'Are you sure you want to revoke all other sessions? This will log you out from all other devices except this one.';
    
    if (!confirm(confirmMessage)) {
      return;
    }

    try {
      setIsRevokingAll(true);
      await userService.revokeAllSessions();
      
      // Keep only current session
      setSessions(prev => prev.filter(session => session.is_current));
      
      // Show success message
      alert('All other sessions have been revoked successfully');
    } catch (error) {
      console.error('Failed to revoke all sessions:', error);
      alert('Failed to revoke all sessions. Please try again.');
    } finally {
      setIsRevokingAll(false);
    }
  };

  const getDeviceIcon = (device: string) => {
    const deviceLower = device.toLowerCase();
    if (deviceLower.includes('mobile') || deviceLower.includes('phone') || deviceLower.includes('android') || deviceLower.includes('ios')) {
      return <Smartphone className="h-5 w-5" />;
    }
    if (deviceLower.includes('desktop') || deviceLower.includes('windows') || deviceLower.includes('mac') || deviceLower.includes('linux')) {
      return <Monitor className="h-5 w-5" />;
    }
    return <Globe className="h-5 w-5" />;
  };

  const formatLastActive = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      return 'Active now';
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
    }
  };

  const otherSessions = sessions.filter(session => !session.is_current);
  const currentSession = sessions.find(session => session.is_current);

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Active Sessions" size="lg">
      <div className="space-y-6">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-600 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="md" />
          </div>
        ) : (
          <>
            {/* Current Session */}
            {currentSession && (
              <div>
                <h3 className="text-sm font-medium text-[hsl(var(--text))] mb-3 flex items-center gap-2">
                  <Shield className="h-4 w-4 text-green-500" />
                  Current Session
                </h3>
                <Card className="p-4">
                  <div className="flex items-center gap-4">
                    <div className="text-[hsl(var(--text))] opacity-60">
                      {getDeviceIcon(currentSession.device)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-[hsl(var(--text))] truncate">
                        {currentSession.device}
                      </div>
                      <div className="text-sm text-[hsl(var(--text))] opacity-70 flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <MapPin className="h-3 w-3" />
                          {currentSession.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {formatLastActive(currentSession.last_active)}
                        </span>
                      </div>
                    </div>
                    <div className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                      Active
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Other Sessions */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-[hsl(var(--text))] flex items-center gap-2">
                  Other Sessions ({otherSessions.length})
                </h3>
                {otherSessions.length > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRevokeAllSessions}
                    disabled={isRevokingAll}
                    className="text-red-600 hover:text-red-700 border-red-200 hover:border-red-300"
                  >
                    {isRevokingAll ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        Revoking...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-3 w-3 mr-1" />
                        Revoke All
                      </>
                    )}
                  </Button>
                )}
              </div>

              {otherSessions.length === 0 ? (
                <Card className="p-6 text-center">
                  <div className="text-[hsl(var(--text))] opacity-60 mb-2">
                    <Shield className="h-8 w-8 mx-auto mb-2" />
                  </div>
                  <div className="text-sm text-[hsl(var(--text))] opacity-70">
                    No other active sessions found. You're only logged in from this device.
                  </div>
                </Card>
              ) : (
                <div className="space-y-3">
                  {otherSessions.map((session) => (
                    <Card key={session.id} className="p-4">
                      <div className="flex items-center gap-4">
                        <div className="text-[hsl(var(--text))] opacity-60">
                          {getDeviceIcon(session.device)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-[hsl(var(--text))] truncate">
                            {session.device}
                          </div>
                          <div className="text-sm text-[hsl(var(--text))] opacity-70 flex items-center gap-3">
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {session.location}
                            </span>
                            <span className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              {formatLastActive(session.last_active)}
                            </span>
                          </div>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRevokeSession(session.id)}
                          disabled={isRevoking === session.id}
                          className="text-red-600 hover:text-red-700 border-red-200 hover:border-red-300"
                        >
                          {isRevoking === session.id ? (
                            <>
                              <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                              Revoking...
                            </>
                          ) : (
                            <>
                              <Trash2 className="h-3 w-3 mr-1" />
                              Revoke
                            </>
                          )}
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>

            {/* Security Notice */}
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
              <div className="flex items-start gap-3">
                <Shield className="h-4 w-4 text-blue-600 mt-0.5" />
                <div className="text-sm">
                  <div className="font-medium text-blue-900 mb-1">Security Notice</div>
                  <div className="text-blue-700">
                    Regularly review your active sessions and revoke any that you don't recognize. 
                    If you notice suspicious activity, change your password immediately.
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Close Button */}
        <div className="flex justify-end pt-4">
          <Button onClick={onClose} disabled={isRevoking !== null || isRevokingAll}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}