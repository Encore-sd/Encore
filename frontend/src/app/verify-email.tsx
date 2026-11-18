import { useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as SecureStore from 'expo-secure-store';
import {
  Alert,
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function VerifyEmailScreen() {
  const router = useRouter();
  const { email } = useLocalSearchParams<{ email: string }>();

  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleVerify = async () => {
    if (!email || !/^\d{6}$/.test(code.trim())) {
      Alert.alert('Invalid code', 'Please enter your six-digit verification code.');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(
        `${process.env.EXPO_PUBLIC_API_URL}/auth/verify-email`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email,
            verificationCode: code.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        Alert.alert('Verification failed', data.message || 'Please try again.');
        return;
      }

      if (!data.token) {
        Alert.alert('Verification failed', 'No authentication token was returned.');
        return;
      }

      await SecureStore.setItemAsync('authToken', data.token);
      router.replace('/dashboard');
    } catch (error) {
      Alert.alert('Connection error', 'Unable to verify your email.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Verify your email</Text>

        <Text style={styles.subtitle}>
          Enter the six-digit verification code sent to {email}.
        </Text>

        <TextInput
          style={styles.input}
          placeholder="000000"
          keyboardType="number-pad"
          maxLength={6}
          value={code}
          onChangeText={setCode}
          textAlign="center"
        />

        <Pressable
          style={styles.button}
          onPress={handleVerify}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Verify email</Text>
          )}
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F7F6FC',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    backgroundColor: '#FFFFFF',
    padding: 24,
    borderRadius: 20,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#24213A',
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 15,
    color: '#6B687A',
    marginBottom: 24,
    lineHeight: 22,
  },
  input: {
    borderWidth: 1,
    borderColor: '#D8D4E8',
    borderRadius: 12,
    padding: 16,
    fontSize: 24,
    letterSpacing: 6,
    marginBottom: 20,
    color: '#24213A',
  },
  button: {
    backgroundColor: '#0D9488',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});