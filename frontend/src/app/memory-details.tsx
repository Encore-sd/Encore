
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import {
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';


export default function MemoryDetailsScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>

        {/* Back button */}
        <Pressable
            style={styles.figmaBackButton}
            onPress={() => router.back()}
        >
            <Ionicons name="chevron-back" size={24} color="#15131D" />
        </Pressable>

        {/* Header */}
        <View style={styles.figmaHeader}>
            <View style={styles.figmaCategoryRow}>
                <Ionicons name="cube-outline" size={17} color="#0E8B7E" />
                <Text style={styles.figmaCategory}>OBJECT</Text>
            </View>

            <Text style={styles.figmaTitle}>Car keys</Text>
            <Text style={styles.figmaSubtitle}>Today · 8:42 AM · 3h ago</Text>

            <Text style={styles.figmaDescription}>
                Your keys were last captured resting beside the
                fruit bowl on the kitchen counter.
            </Text>
        </View>

        {/* Map preview */}
        <View style={styles.mapPreviewCard}>
            <View style={styles.mapIllustration}>
                <View style={styles.mapRoadHorizontal} />
                <View style={styles.mapRoadDiagonal} />

                <View style={styles.mapPin}>
                    <Ionicons name="location" size={24} color="#0E8B7E" />
                </View>

                <View style={styles.mapLocationLabel}>
                    <Text style={styles.mapLocationText}>Home · Kitchen</Text>
                </View>
            </View>

            <Pressable style={styles.openMapButton}>
                <Text style={styles.openMapText}>Open in Map ›</Text>
            </Pressable>
        </View>

        {/* Memory information */}
        <View style={styles.detailsList}>
            <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Captured</Text>
                <Text style={styles.detailValue}>8:42 AM</Text>
            </View>

            <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Place</Text>
                <Text style={styles.detailValue}>Home · Kitchen</Text>
            </View>

            <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Photo</Text>
                <Text style={styles.detailMuted}>Not captured</Text>
            </View>

            <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>In your day</Text>
                <Pressable onPress={() => router.replace('/memories')}>
                    <Text style={styles.timelineLink}>See in timeline</Text>
                </Pressable>
            </View>
        </View>

        {/* Map button - placeholder */}
        <Pressable style={styles.mapButton}>
          <Ionicons name="map-outline" size={20} color="#6044DC" />
          <Text style={styles.mapButtonText}>View on map</Text>
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
    paddingTop: 25,
    paddingBottom: 50,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 30,
  },
  backText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#6044DC',
  },
  header: {
    alignItems: 'center',
    marginBottom: 35,
  },
  iconCircle: {
    width: 68,
    height: 68,
    borderRadius: 34,
    backgroundColor: '#E5F4F0',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  category: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
    color: '#0E8B7E',
    marginBottom: 10,
  },
  title: {
    fontSize: 30,
    fontWeight: '700',
    color: '#15131D',
    marginBottom: 9,
  },
  subtitle: {
    fontSize: 13,
    color: '#5E5A6E',
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.3,
    color: '#5E5A6E',
    marginBottom: 12,
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    marginBottom: 26,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 13,
  },
  infoText: {
    flex: 1,
  },
  infoTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#15131D',
  },
  infoSubtitle: {
    fontSize: 13,
    color: '#5E5A6E',
    marginTop: 4,
  },
  description: {
    fontSize: 15,
    lineHeight: 24,
    color: '#242137',
  },
  divider: {
    height: 1,
    backgroundColor: '#E6E3EF',
    marginVertical: 20,
  },
  mapButton: {
    backgroundColor: '#EEEAFB',
    borderRadius: 18,
    paddingVertical: 17,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  mapButtonText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#6044DC',
  },
  figmaBackButton: {
  width: 48,
  height: 48,
  borderRadius: 15,
  backgroundColor: '#FFFFFF',
  borderWidth: 1,
  borderColor: '#E6E3EF',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: 26,
    },

    figmaHeader: {
    alignItems: 'flex-start',
    marginBottom: 28,
    },

    figmaCategoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    },

    figmaCategory: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5,
    color: '#0E8B7E',
    },

    figmaTitle: {
    fontSize: 32,
    fontWeight: '400',
    color: '#15131D',
    marginBottom: 5,
    },

    figmaSubtitle: {
    fontSize: 13,
    color: '#5E5A6E',
    },

    figmaDescription: {
    fontSize: 16,
    lineHeight: 25,
    color: '#15131D',
    marginTop: 26,
    },
    mapPreviewCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    marginBottom: 20,
    },

    mapIllustration: {
    height: 150,
    backgroundColor: '#E8E2F6',
    borderRadius: 18,
    overflow: 'hidden',
    position: 'relative',
    },

    mapRoadHorizontal: {
    position: 'absolute',
    top: 35,
    left: -20,
    width: '115%',
    height: 15,
    backgroundColor: '#FFFFFF',
    transform: [{ rotate: '-9deg' }],
    },

    mapRoadDiagonal: {
    position: 'absolute',
    right: 45,
    top: -25,
    width: 16,
    height: 230,
    backgroundColor: '#FFFFFF',
    transform: [{ rotate: '25deg' }],
    },

    mapPin: {
    position: 'absolute',
    top: 50,
    left: '48%',
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#D7F3E9',
    alignItems: 'center',
    justifyContent: 'center',
    },

    mapLocationLabel: {
    position: 'absolute',
    right: 10,
    top: 12,
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 9,
    },

    mapLocationText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#15131D',
    },

    openMapButton: {
    paddingVertical: 22,
    alignItems: 'center',
    },

    openMapText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#6044DC',
    },

    detailsList: {
    marginTop: 4,
    },

    detailRow: {
    minHeight: 65,
    borderTopWidth: 1,
    borderTopColor: '#E6E3EF',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 4,
    },

    detailLabel: {
    fontSize: 15,
    color: '#5E5A6E',
    },

    detailValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#15131D',
    },

    detailMuted: {
    fontSize: 14,
    color: '#5E5A6E',
    fontWeight: '600',
    },

    timelineLink: {
    fontSize: 14,
    color: '#6044DC',
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
    justifyContent: 'center',
    gap: 5,
  },
  navText: {
    fontSize: 11,
    color: '#777387',
    fontWeight: '600',
  },
});
