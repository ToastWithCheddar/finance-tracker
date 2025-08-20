import { useState } from 'react';
import { Edit2, Mail, Calendar, MapPin, Globe, DollarSign, CheckCircle, XCircle } from 'lucide-react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { formatDate, getUserInitials, getDisplayName } from '../../utils';
import type { UserProfile } from '../../services/userService';

interface ProfileInfoProps {
  profile: UserProfile;
  onEdit: () => void;
  className?: string;
}

export function ProfileInfo({ profile, onEdit, className = '' }: ProfileInfoProps) {
  const [imageError, setImageError] = useState(false);

  return (
    <Card className={className}>
      <div className="p-6">
        <div className="flex items-start justify-between mb-6">
          <h2 className="text-xl font-semibold text-[hsl(var(--text))]">Profile Information</h2>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onEdit}
            className="flex items-center gap-2"
          >
            <Edit2 className="h-4 w-4" />
            Edit
          </Button>
        </div>

        <div className="flex flex-col md:flex-row gap-6">
          {/* Avatar Section */}
          <div className="flex flex-col items-center md:items-start">
            <div className="w-24 h-24 rounded-full overflow-hidden bg-gradient-to-br from-[hsl(var(--brand))] to-blue-500 flex items-center justify-center text-white text-2xl font-bold mb-3">
              {profile.avatar_url && !imageError ? (
                <img
                  src={profile.avatar_url}
                  alt="Profile"
                  className="w-full h-full object-cover"
                  onError={() => setImageError(true)}
                />
              ) : (
                getUserInitials(profile)
              )}
            </div>
            <div className="text-center md:text-left">
              <div className="flex items-center gap-2">
                {profile.is_verified ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-yellow-500" />
                )}
                <span className="text-sm text-[hsl(var(--text))] opacity-70">
                  {profile.is_verified ? 'Verified Account' : 'Unverified Account'}
                </span>
              </div>
            </div>
          </div>

          {/* Profile Details */}
          <div className="flex-1 space-y-4">
            <div>
              <h3 className="text-lg font-medium text-[hsl(var(--text))]">
                {getDisplayName(profile)}
              </h3>
              {profile.display_name && (profile.first_name || profile.last_name) && (
                <p className="text-sm text-[hsl(var(--text))] opacity-70">
                  {profile.first_name} {profile.last_name}
                </p>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                <div>
                  <div className="text-sm font-medium text-[hsl(var(--text))]">Email</div>
                  <div className="text-sm text-[hsl(var(--text))] opacity-70">{profile.email}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                <div>
                  <div className="text-sm font-medium text-[hsl(var(--text))]">Member Since</div>
                  <div className="text-sm text-[hsl(var(--text))] opacity-70">{formatDate(profile.created_at)}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <MapPin className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                <div>
                  <div className="text-sm font-medium text-[hsl(var(--text))]">Timezone</div>
                  <div className="text-sm text-[hsl(var(--text))] opacity-70">{profile.timezone}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Globe className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                <div>
                  <div className="text-sm font-medium text-[hsl(var(--text))]">Locale</div>
                  <div className="text-sm text-[hsl(var(--text))] opacity-70">{profile.locale}</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <DollarSign className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                <div>
                  <div className="text-sm font-medium text-[hsl(var(--text))]">Currency</div>
                  <div className="text-sm text-[hsl(var(--text))] opacity-70">{profile.currency}</div>
                </div>
              </div>

              {profile.updated_at && (
                <div className="flex items-center gap-3">
                  <Edit2 className="h-4 w-4 text-[hsl(var(--text))] opacity-60" />
                  <div>
                    <div className="text-sm font-medium text-[hsl(var(--text))]">Last Updated</div>
                    <div className="text-sm text-[hsl(var(--text))] opacity-70">{formatDate(profile.updated_at)}</div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}