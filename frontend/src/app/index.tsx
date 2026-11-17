
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

export default function LoginScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<'signin' | 'register'>('signin');
  const [email, setEmail] = useState('maya@email.com');
  const [password, setPassword] = useState('encore2025');

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
      >
        {/* Encore logo */}
        <View style={styles.logo}>
          <View style={styles.logoMark}>
            <View style={styles.logoCenter} />
          </View>
          <Text style={styles.logoText}>encore</Text>
        </View>

        <Text style={styles.heading}>Find what you forgot.</Text>

        {/* Sign in / Create account tabs */}
        <View style={styles.authSwitch}>
          <Pressable
            style={[
              styles.authTab,
              mode === 'signin' && styles.activeTab,
            ]}
            onPress={() => setMode('signin')}
          >
            <Text
              style={[
                styles.tabText,
                mode === 'signin' && styles.activeTabText,
              ]}
            >
              Sign in
            </Text>
          </Pressable>

          <Pressable
            style={[
              styles.authTab,
              mode === 'register' && styles.activeTab,
            ]}
            onPress={() => setMode('register')}
          >
            <Text
              style={[
                styles.tabText,
                mode === 'register' && styles.activeTabText,
              ]}
            >
              Create account
            </Text>
          </Pressable>
        </View>

        {/* Email */}
        <Text style={styles.label}>Email</Text>
        <TextInput
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
          placeholder="Email address"
        />

        {/* Password */}
        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder="Password"
        />

        {/* Primary button */}
        <Pressable
          style={styles.loginButton}
          onPress={() => router.replace('/dashboard')}
        >
          <Text style={styles.loginButtonText}>
            {mode === 'signin' ? 'Sign in' : 'Create account'}
          </Text>
        </Pressable>

        {mode === 'signin' && (
          <Pressable style={styles.forgotButton}>
            <Text style={styles.forgotText}>
              Forgot password?
            </Text>
          </Pressable>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const colors = {
  background: '#F4F3F8',
  card: '#FFFFFF',
  ink: '#15131D',
  muted: '#5E5A6E',
  line: '#E6E3EF',
  violet: '#5B3FD6',
  violetTint: '#EEEAFB',
  teal: '#0E7C70',
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: 28,
    paddingTop: 70,
    paddingBottom: 30,
  },
  logo: {
    alignItems: 'center',
    gap: 14,
  },
  logoMark: {
    width: 44,
    height: 44,
    borderWidth: 4,
    borderColor: colors.violet,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoCenter: {
    width: 11,
    height: 11,
    borderRadius: 6,
    backgroundColor: colors.teal,
  },
  logoText: {
    fontSize: 34,
    fontWeight: '800',
    letterSpacing: -1.6,
    color: colors.ink,
  },
  heading: {
    fontSize: 24,
    fontWeight: '700',
    letterSpacing: -0.6,
    textAlign: 'center',
    color: colors.ink,
    marginTop: 20,
    marginBottom: 27,
  },
  authSwitch: {
    flexDirection: 'row',
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 3,
    marginBottom: 22,
  },
  authTab: {
    flex: 1,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
  },
  activeTab: {
    backgroundColor: colors.violetTint,
  },
  tabText: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.muted,
  },
  activeTabText: {
    color: colors.violet,
  },
  label: {
    fontSize: 11,
    fontWeight: '800',
    color: colors.muted,
    marginBottom: 7,
  },
  input: {
    height: 54,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.card,
    paddingHorizontal: 15,
    fontSize: 14,
    fontWeight: '600',
    color: colors.ink,
    marginBottom: 14,
  },
  loginButton: {
    height: 48,
    marginTop: 4,
    borderRadius: 14,
    backgroundColor: colors.violet,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loginButtonText: {
    fontSize: 13,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  forgotButton: {
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
  },
  forgotText: {
    fontSize: 12,
    fontWeight: '800',
    color: colors.violet,
  },
});
