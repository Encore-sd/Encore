import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import {
    Pressable,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

type Category = 'Place' | 'Talk' | 'Object';
type Filter = 'All' | 'Objects' | 'Talks' | 'Places';

const memories: {
  id: number;
  time: string;
  category: Category;
  title: string;
  subtitle: string;
  details: string;
}[] = [
  {
    id: 1,
    time: '11:05',
    category: 'Place',
    title: 'Campus Garage',
    subtitle: 'Arrived on level 2',
    details: 'You arrived at Campus Garage and parked on level 2.',
  },
  {
    id: 2,
    time: '9:30',
    category: 'Talk',
    title: 'Friday lunch',
    subtitle: '“Let’s push Friday lunch to one.”',
    details: 'A conversation about moving Friday lunch to 1:00 PM.',
  },
  {
    id: 3,
    time: '8:42',
    category: 'Object',
    title: 'Car keys',
    subtitle: 'Home · Kitchen',
    details: 'Last seen on the kitchen counter beside the fruit bowl.',
  },
];

const categoryColors = {
  Place: '#242137',
  Talk: '#6044DC',
  Object: '#0E8B7E',
};

const categoryIcons = {
  Place: 'location-outline',
  Talk: 'chatbubble-outline',
  Object: 'cube-outline',
} as const;

export default function MemoriesScreen() {
  const router = useRouter();
  const [filter, setFilter] = useState<Filter>('All');
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<number | null>(3);

  const filteredMemories = memories.filter((memory) => {
    const matchesCategory =
      filter === 'All' ||
      (filter === 'Objects' && memory.category === 'Object') ||
      (filter === 'Talks' && memory.category === 'Talk') ||
      (filter === 'Places' && memory.category === 'Place');

    const matchesSearch =
      memory.title.toLowerCase().includes(search.toLowerCase()) ||
      memory.subtitle.toLowerCase().includes(search.toLowerCase());

    return matchesCategory && matchesSearch;
  });

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <Text style={styles.heading}>Memories</Text>

        <View style={styles.searchRow}>
          <View style={styles.searchBox}>
            <Ionicons name="search-outline" size={23} color="#6044DC" />
            <TextInput
              style={styles.searchInput}
              placeholder={'Search or ask “where are my keys?”'}
              placeholderTextColor="#5E5A6E"
              value={search}
              onChangeText={setSearch}
              multiline
            />
          </View>

          <Pressable style={styles.filterIcon}>
            <Ionicons name="filter-outline" size={23} color="#6044DC" />
          </Pressable>
        </View>

        <View style={styles.filterRow}>
          {(['All', 'Objects', 'Talks', 'Places'] as Filter[]).map((item) => (
            <Pressable
              key={item}
              onPress={() => setFilter(item)}
              style={[
                styles.filterButton,
                filter === item && styles.activeFilter,
              ]}
            >
              <Text
                style={[
                  styles.filterText,
                  filter === item && styles.activeFilterText,
                ]}
              >
                {item}
              </Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.dateLabel}>TODAY · OCT 25</Text>

        <View style={styles.timeline}>
          <View style={styles.timelineLine} />

          {filteredMemories.map((memory) => {
            const isExpanded = expanded === memory.id;
            const color = categoryColors[memory.category];

            return (
              <View key={memory.id} style={styles.timelineRow}>
                <Text style={styles.time}>{memory.time}</Text>

                <View style={styles.dotColumn}>
                  <View style={[styles.dot, { backgroundColor: color }]} />
                </View>

                <Pressable
                    style={styles.memoryCard}
                    onPress={() => {
                        if (memory.id === 3) {
                        router.push('/memory-details');
                        } else {
                        setExpanded(isExpanded ? null : memory.id);
                        }
                    }}
                >
                  <View style={styles.categoryRow}>
                    <Ionicons
                      name={categoryIcons[memory.category]}
                      size={16}
                      color={color}
                    />
                    <Text style={[styles.category, { color }]}>
                      {memory.category.toUpperCase()}
                    </Text>
                    <Ionicons
                      name={isExpanded ? 'chevron-up' : 'chevron-down'}
                      size={19}
                      color="#242137"
                      style={styles.chevron}
                    />
                  </View>

                  <Text style={styles.memoryTitle}>{memory.title}</Text>
                  <Text style={styles.memorySubtitle}>{memory.subtitle}</Text>

                  {isExpanded && (
                    <View style={styles.expandedContent}>
                      <Text style={styles.memoryDetails}>
                        {memory.details}
                      </Text>
                      <Pressable>
                        <Text style={styles.mapLink}>View on map</Text>
                      </Pressable>
                    </View>
                  )}
                </Pressable>
              </View>
            );
          })}
        </View>
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

        <Pressable style={styles.navItem}>
          <View style={styles.activeIcon}>
            <Ionicons name="reader-outline" size={23} color="#6044DC" />
          </View>
          <Text style={styles.activeNavText}>Memories</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
          <Ionicons name="map-outline" size={23} color="#777387" />
          <Text style={styles.navText}>Map</Text>
        </Pressable>

        <Pressable style={styles.navItem}>
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
    paddingTop: 32,
    paddingBottom: 50,
  },
  heading: {
    fontSize: 30,
    fontWeight: '400',
    color: '#15131D',
    marginBottom: 24,
  },
  searchRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 14,
  },
  searchBox: {
    flex: 1,
    minHeight: 65,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    paddingHorizontal: 16,
    gap: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    color: '#15131D',
    paddingVertical: 10,
    maxHeight: 75,
  },
  filterIcon: {
    width: 62,
    borderRadius: 18,
    backgroundColor: '#EEEAFB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterRow: {
    flexDirection: 'row',
    gap: 7,
    marginBottom: 32,
  },
  filterButton: {
    paddingHorizontal: 13,
    paddingVertical: 12,
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E6E3EF',
  },
  activeFilter: {
    backgroundColor: '#EEEAFB',
    borderColor: '#6044DC',
  },
  filterText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#5E5A6E',
  },
  activeFilterText: {
    color: '#6044DC',
  },
  dateLabel: {
    fontSize: 11,
    letterSpacing: 1.4,
    fontWeight: '700',
    color: '#5E5A6E',
    marginBottom: 18,
  },
  timeline: {
    position: 'relative',
  },
  timelineLine: {
    position: 'absolute',
    left: 58,
    top: 16,
    bottom: 35,
    width: 2,
    backgroundColor: '#E6E3EF',
  },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 20,
    minHeight: 116,
  },
  time: {
    width: 49,
    paddingTop: 14,
    fontSize: 10,
    letterSpacing: 0.5,
    color: '#5E5A6E',
    fontWeight: '600',
  },
  dotColumn: {
    width: 20,
    alignItems: 'center',
    paddingTop: 17,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  memoryCard: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E6E3EF',
    shadowColor: '#252044',
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 2,
  },
  categoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  category: {
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
  chevron: {
    marginLeft: 'auto',
  },
  memoryTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#15131D',
    marginBottom: 5,
  },
  memorySubtitle: {
    fontSize: 13,
    color: '#5E5A6E',
    lineHeight: 19,
  },
  expandedContent: {
    marginTop: 14,
    gap: 12,
  },
  memoryDetails: {
    fontSize: 13,
    color: '#5E5A6E',
    lineHeight: 19,
  },
  mapLink: {
    color: '#6044DC',
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
