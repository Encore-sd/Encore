
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
    Pressable,
    ScrollView,
    StyleSheet,
    Switch,
    Text,
    View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function SettingsScreen() {
  const router = useRouter();
  const [recording, setRecording] = useState(true);
  const [notifications, setNotifications] = useState(true);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.heading}>Settings</Text>

        {/* Profile */}
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>M</Text>
          </View>
          <View>
            <Text style={styles.profileName}>Maya</Text>
            <Text style={styles.profileEmail}>maya@email.com</Text>
          </View>
        </View>

        {/* Device */}
        <Text style={styles.sectionTitle}>DEVICE</Text>
        <View style={styles.card}>
          <View style={styles.settingRow}>
            <Ionicons name="watch-outline" size={23} color="#6044DC" />
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Encore Band</Text>
              <Text style={styles.settingSubtitle}>Connected · Battery 82%</Text>
            </View>
            <View style={styles.statusDot} />
          </View>

          <View style={styles.divider} />

          <View style={styles.settingRow}>
            <Ionicons name="mic-outline" size={23} color="#6044DC" />
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Recording</Text>
              <Text style={styles.settingSubtitle}>
                {recording ? 'Currently capturing' : 'Recording paused'}
              </Text>
            </View>
            <Switch
              value={recording}
              onValueChange={setRecording}
              trackColor={{ false: '#D8D5E3', true: '#B9A9F2' }}
              thumbColor={recording ? '#6044DC' : '#FFFFFF'}
            />
          </View>
        </View>

        {/* Preferences */}
        <Text style={styles.sectionTitle}>PREFERENCES</Text>
        <View style={styles.card}>
          <View style={styles.settingRow}>
            <Ionicons
              name="notifications-outline"
              size={23}
              color="#6044DC"
            />
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Notifications</Text>
              <Text style={styles.settingSubtitle}>
                Memory reminders and updates
              </Text>
            </View>
            <Switch
              value={notifications}
              onValueChange={setNotifications}
              trackColor={{ false: '#D8D5E3', true: '#B9A9F2' }}
              thumbColor={notifications ? '#6044DC' : '#FFFFFF'}
            />
          </View>

          <View style={styles.divider} />

          <View style={styles.settingRow}>
            <Ionicons name="moon-outline" size={23} color="#6044DC" />
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Appearance</Text>
              <Text style={styles.settingSubtitle}>Light mode</Text>
            </View>
            <Ionicons name="chevron-forward" size={19} color="#9993AA" />
          </View>
        </View>

        {/* Privacy */}
        <Text style={styles.sectionTitle}>PRIVACY & DATA</Text>
        <View style={styles.card}>
          <View style={styles.settingRow}>
            <Ionicons name="lock-closed-outline" size={23} color="#6044DC" />
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Privacy settings</Text>
              <Text style={styles.settingSubtitle}>
                Manage your memory preferences
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={19} color="#9993AA" />
          </View>

          <View style={styles.divider} />

          <View style={styles.settingRow}>
            <Ionicons name="server-outline" size={23} color="#6044DC" />
            <View style={styles.settingInfo}>
              <Text style={styles.settingTitle}>Data management</Text>
              <Text style={styles.settingSubtitle}>
                Review and manage saved data
              </Text>
            </View>
            <Ionicons name="chevron-forward" size={19} color="#9993AA" />
          </View>
        </View>

        <Pressable
          style={styles.signOutButton}
          onPress={() => router.replace('/')}
        >
          <Ionicons name="log-out-outline" size={20} color="#B34B60" />
          <Text style={styles.signOutText}>Sign out</Text>
        </Pressable>
      </ScrollView>

      {/* Bottom navigation */}
      <View style={styles.bottomNav}>
        <Pressable
          style={styles.navItem}
          onPress={() => router.replace('/dashboard')}
        >
          <Ionicons name="home-outline" size={23} color="#777387" />
          <Text style={styles.navText}>Home</Text>
        </Pressable>

        <Pressable
          style={styles.navItem}
          onPress={() => router.replace('/memories')}
        >
          <Ionicons name="albums-outline" size={23} color="#777387" />
          <Text style={styles.navText}>Memories</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
          <Ionicons name="map-outline" size={23} color="#777387" />
          <Text style={styles.navText}>Map</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
          <View style={styles.activeIcon}>
            <Ionicons name="settings" size={23} color="#6044DC" />
          </View>
          <Text style={styles.activeNavText}>Settings</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F4FA',
  },
  content: {
    paddingHorizontal: 20,
    paddingTop: 30,
    paddingBottom: 50,
  },
  heading: {
    fontSize: 30,
    fontWeight: '400',
    color: '#15131D',
    marginBottom: 24,
  },
  profileCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 18,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 15,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    marginBottom: 30,
  },
  avatar: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: '#EEEAFB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: '#6044DC',
    fontSize: 22,
    fontWeight: '700',
  },
  profileName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#15131D',
  },
  profileEmail: {
    fontSize: 13,
    color: '#5E5A6E',
    marginTop: 5,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.4,
    color: '#5E5A6E',
    marginBottom: 12,
    marginTop: 10,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    marginBottom: 24,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 18,
    gap: 13,
  },
  settingInfo: {
    flex: 1,
  },
  settingTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#15131D',
  },
  settingSubtitle: {
    fontSize: 12,
    color: '#5E5A6E',
    marginTop: 5,
  },
  divider: {
    height: 1,
    backgroundColor: '#E6E3EF',
  },
  statusDot: {
    width: 11,
    height: 11,
    borderRadius: 6,
    backgroundColor: '#0E8B7E',
  },
  signOutButton: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E6E3EF',
    borderRadius: 18,
    padding: 18,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    marginTop: 8,
  },
  signOutText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#B34B60',
  },
    bottomNav: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: '#E6E3EF',
    paddingTop: 12,
    paddingBottom: 8,
    justifyContent: 'space-around',
  },
  navItem: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
  },
  activeIcon: {
    backgroundColor: '#EEEAFB',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 4,
  },
  navText: {
    fontSize: 11,
    color: '#777387',
    fontWeight: '600',
  },
  activeNavText: {
    fontSize: 11,
    color: '#6044DC',
    fontWeight: '700',
  },
});
