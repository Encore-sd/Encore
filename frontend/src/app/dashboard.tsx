
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function DashboardScreen() {
  const router = useRouter();
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.brand}>
            <View style={styles.logoRing}>
              <View style={styles.logoDot} />
            </View>
            <Text style={styles.logoText}>encore</Text>
          </View>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>M</Text>
          </View>
        </View>

        {/* Greeting */}
        <View style={styles.greeting}>
          <Text style={styles.date}>SUNDAY · OCT 25</Text>
          <Text style={styles.greetingText}>Good afternoon, Maya</Text>
        </View>

        {/* Device status */}
        <View style={styles.card}>
          <View style={styles.deviceRow}>
            <View style={styles.iconCircle}>
              <Ionicons name="mic-outline" size={22} color="#0E7C70" />
            </View>
            <View style={styles.deviceInfo}>
              <Text style={styles.deviceTitle}>Encore Band</Text>
              <Text style={styles.deviceStatus}>
                <Text style={styles.greenDot}>● </Text>
                Connected · Recording
              </Text>
            </View>
            <View style={styles.battery}>
              <Ionicons name="battery-half-outline" size={22} color="#656078" />
              <Text style={styles.batteryText}>82%</Text>
            </View>
          </View>
        </View>

        {/* Search */}
        <View style={styles.searchCard}>
          <Ionicons name="search-outline" size={24} color="#6044DC" />
          <Text style={styles.searchPlaceholder} numberOfLines={1}>
            Search or ask “where are my keys?”
          </Text>
          <Pressable style={styles.micButton}>
            <Ionicons name="mic-outline" size={23} color="#FFFFFF" />
          </Pressable>
        </View>

        {/* Today's summary */}
        <View style={styles.summaryCard}>
          <View style={styles.summaryTop}>
            <Text style={styles.summaryLabel}>YOUR ENCORE TODAY</Text>
            <View style={styles.captureBadge}>
              <Text style={styles.captureBadgeText}>● Capturing</Text>
            </View>
          </View>

          <View style={styles.memoryRow}>
            <Text style={styles.memoryNumber}>14</Text>
            <Text style={styles.memoryLabel}>memories{'\n'}saved</Text>
          </View>

          <View style={styles.locationRow}>
            <View style={styles.locationIcon}>
              <Ionicons name="location-outline" size={23} color="#242137" />
            </View>
            <View>
              <Text style={styles.locationTitle}>3 locations</Text>
              <Text style={styles.locationSubtitle}>
                Home, Cafe Lumen, Campus Garage
              </Text>
            </View>
          </View>

          <Text style={styles.lastSaved}>
            Last saved at 12:04 PM, Cafe Lumen.
          </Text>

          <Pressable style={styles.browseButton}>
            <Text style={styles.browseText}>
              Browse today's memories  ›
            </Text>
          </Pressable>
        </View>

        {/* Quick Capture */}
        <View style={styles.quickCard}>
          <View style={styles.quickIcon}>
            <Ionicons name="bookmark-outline" size={23} color="#6044DC" />
          </View>
          <View style={styles.quickInfo}>
            <Text style={styles.quickTitle}>Quick Capture</Text>
            <Text style={styles.quickSubtitle}>Mark a moment to remember</Text>
          </View>
          <Pressable style={styles.markButton}>
            <Ionicons name="add" size={18} color="#FFFFFF" />
            <Text style={styles.markText}>Mark</Text>
          </Pressable>
        </View>
      </ScrollView>

      {/* Bottom Navigation */}
      <View style={styles.bottomNav}>
        <Pressable style={styles.navItem}>
          <Ionicons name="home" size={23} color="#6044DC" />
          <Text style={styles.activeNavText}>Home</Text>
        </Pressable>

        <Pressable
          style={styles.navItem}
          onPress={() => router.push('/memories')}
        >
          <Ionicons name="albums-outline" size={23} color="#777387" />
          <Text style={styles.navText}>Memories</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
          <Ionicons name="map-outline" size={23} color="#777387" />
          <Text style={styles.navText}>Map</Text>
        </Pressable>

        <Pressable
            style={styles.navItem}
            onPress={() => router.replace('/settings')}
        >
            <Ionicons name="settings-outline" size={23} color="#777387" />
            <Text style={styles.navText}>Settings</Text>
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
    paddingTop: 16,
    paddingBottom: 32,
    gap: 18,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 28,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  logoRing: {
    width: 38,
    height: 38,
    borderWidth: 3,
    borderColor: '#6044DC',
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoDot: {
    width: 10,
    height: 10,
    backgroundColor: '#0E7C70',
    borderRadius: 5,
  },
  logoText: {
    fontSize: 25,
    fontWeight: '800',
    color: '#15131D',
    letterSpacing: -1,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#EEEAFB',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    fontSize: 17,
    fontWeight: '700',
    color: '#6044DC',
  },
  greeting: {
    gap: 12,
    marginBottom: 6,
  },
  date: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
    color: '#5E5A6E',
  },
  greetingText: {
    fontSize: 27,
    fontWeight: '400',
    color: '#15131D',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    padding: 16,
    shadowColor: '#252044',
    shadowOpacity: 0.07,
    shadowRadius: 12,
    elevation: 3,
  },
  deviceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#DFF2ED',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deviceInfo: {
    flex: 1,
    gap: 6,
  },
  deviceTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#15131D',
  },
  deviceStatus: {
    fontSize: 12,
    color: '#5E5A6E',
  },
  greenDot: {
    color: '#0E7C70',
  },
  battery: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  batteryText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#5E5A6E',
  },
  searchCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    paddingLeft: 18,
    paddingRight: 10,
    height: 72,
    gap: 12,
    shadowColor: '#252044',
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 2,
  },
  searchPlaceholder: {
    flex: 1,
    color: '#5E5A6E',
    fontSize: 14,
  },
  micButton: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: '#6044DC',
    alignItems: 'center',
    justifyContent: 'center',
  },
  summaryCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    paddingTop: 20,
    paddingHorizontal: 18,
    overflow: 'hidden',
    shadowColor: '#252044',
    shadowOpacity: 0.07,
    shadowRadius: 12,
    elevation: 3,
  },
  summaryTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1.2,
    color: '#5E5A6E',
  },
  captureBadge: {
    backgroundColor: '#DFF2ED',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  captureBadgeText: {
    fontSize: 12,
    color: '#5E5A6E',
  },
  memoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginTop: 20,
  },
  memoryNumber: {
    fontSize: 64,
    fontWeight: '700',
    color: '#15131D',
    letterSpacing: -3,
  },
  memoryLabel: {
    fontSize: 16,
    color: '#5E5A6E',
    lineHeight: 21,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginTop: 8,
  },
  locationIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#F0EFF5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  locationTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#15131D',
  },
  locationSubtitle: {
    fontSize: 12,
    color: '#5E5A6E',
    marginTop: 5,
  },
  lastSaved: {
    fontSize: 12,
    color: '#5E5A6E',
    marginTop: 20,
    marginBottom: 16,
  },
  browseButton: {
    borderTopWidth: 1,
    borderTopColor: '#E6E3EF',
    paddingVertical: 18,
    alignItems: 'center',
    marginHorizontal: -18,
  },
  browseText: {
    color: '#6044DC',
    fontSize: 13,
    fontWeight: '700',
  },
  quickCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    shadowColor: '#252044',
    shadowOpacity: 0.07,
    shadowRadius: 12,
    elevation: 2,
  },
  quickIcon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: '#EEEAFB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickInfo: {
    flex: 1,
    gap: 5,
  },
  quickTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#15131D',
  },
  quickSubtitle: {
    fontSize: 11,
    color: '#5E5A6E',
  },
  markButton: {
    backgroundColor: '#6044DC',
    borderRadius: 15,
    paddingHorizontal: 15,
    height: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  markText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
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
    gap: 5,
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
