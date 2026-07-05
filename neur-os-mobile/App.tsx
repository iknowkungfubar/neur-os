import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, TextInput, TouchableOpacity, FlatList, SafeAreaView, StatusBar, ScrollView, Alert } from 'react-native';
import { EnergyBattery, energyEnvelope } from '../shared/domain';
import { cacheState, getCachedState, saveLocal, loadLocal } from '../shared/storage';

let API = 'http://localhost:7447/api';

async function api(path: string, opts?: any) {
  try {
    const res = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opts,
    });
    return res.json();
  } catch {
    return null;
  }
}

export default function App() {
  const [tab, setTab] = useState<'today' | 'tasks' | 'focus' | 'review'>('today');
  const [state, setState] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [dumpText, setDumpText] = useState('');
  const [dumpResult, setDumpResult] = useState<any>(null);
  const [menu, setMenu] = useState<any>(null);
  const [listening, setListening] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState(API);
  const [battery, setBattery] = useState(new EnergyBattery(50, 0.5, 0.3));

  const saveApiUrl = () => { API = apiUrl.replace(/\/$/, ''); setShowSettings(false); Alert.alert('API', 'URL updated'); };

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) { alert('Voice not supported in this browser'); return; }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.onresult = (e: any) => {
      const text = e.results[0][0].transcript;
      setDumpText(text);
      setListening(false);
    };
    recognition.onerror = () => setListening(false);
    recognition.start();
    setListening(true);
  };

  const refresh = useCallback(async () => {
    // Load from cache first for instant display
    const cached = await getCachedState();
    if (cached) {
      setState(cached);
      setBattery(new EnergyBattery(cached.remaining_spoons / (cached.total_spoons || 10) * 100));
    }
    // Then fetch fresh data from server
    const s = await api('/state');
    if (s?.state) {
      setState(s.state);
      setBattery(new EnergyBattery(
        (s.state.remaining_spoons / (s.state.total_spoons || 10)) * 100
      ));
      await cacheState(s.state);
    }
    const t = await api('/tasks');
    if (t?.tasks) setTasks(t.tasks);
  }, []);

  useEffect(() => { refresh(); const id = setInterval(refresh, 30000); return () => clearInterval(id); }, []);

  const doBrainDump = async () => {
    if (!dumpText.trim()) return;
    const d = await api('/brain-dump', { method: 'POST', body: JSON.stringify({ text: dumpText }) });
    if (d) {
      setDumpResult(d);
      setDumpText('');
      refresh();
    } else {
      // Offline: save locally and sync later
      await saveLocal('pending-dump-' + Date.now(), dumpText);
      setDumpResult({ structured: { tasks: [{ title: dumpText }], notes: [] } });
      setDumpText('');
      Alert.alert('Saved offline', 'Will sync when connection returns');
    }
  };

  const loadMenu = async () => {
    const m = await api('/dopamine-menu');
    if (m) setMenu(m);
  };

  const pct = battery.percentage;
  const env = energyEnvelope(pct, tasks.filter((t: any) => t.status !== 'done').length, []);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#0a0a0f' }}>
      <StatusBar barStyle="light-content" />
      <View style={{ flex: 1, padding: 16 }}>
        {/* Tab bar */}
        <View style={{ flexDirection: 'row', gap: 8, marginBottom: 16 }}>
          {(['today', 'tasks', 'focus', 'review'] as const).map(t => (
            <TouchableOpacity key={t} onPress={() => { setTab(t); if (t === 'tasks') loadMenu(); }}
              style={{ paddingVertical: 8, paddingHorizontal: 16, borderRadius: 8, backgroundColor: tab === t ? '#2a2a3a' : '#1a1a2a' }}>
              <Text style={{ color: tab === t ? '#fff' : '#888' }}>{t}</Text>
            </TouchableOpacity>
          ))}
          <TouchableOpacity onPress={() => setShowSettings(!showSettings)} style={{ marginLeft: 'auto', padding: 8 }}>
            <Text style={{ color: '#666' }}>⚙</Text>
          </TouchableOpacity>
        </View>
        {showSettings && (
          <View style={{ backgroundColor: '#1a1a2a', padding: 12, borderRadius: 8, marginBottom: 16 }}>
            <TextInput style={{ backgroundColor: '#2a2a3a', color: '#fff', padding: 8, borderRadius: 4, marginBottom: 8 }}
              value={apiUrl} onChangeText={setApiUrl} placeholder="http://host:7447/api" placeholderTextColor="#666" />
            <TouchableOpacity onPress={saveApiUrl} style={{ backgroundColor: '#22c55e', padding: 8, borderRadius: 4, alignItems: 'center' }}>
              <Text style={{ color: '#fff' }}>Save</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Today tab */}
        {tab === 'today' && (
          <ScrollView>
            <Text style={{ fontSize: 24, color: '#fff', marginBottom: 16 }}>How are things today?</Text>
            <Text style={{ fontSize: 40, color: pct > 50 ? '#4ade80' : pct > 20 ? '#fbbf24' : '#f87171', marginBottom: 16 }}>
              {Math.round(pct)}%
            </Text>
            <Text style={{ color: '#666', marginBottom: 8 }}>
              Status: {env.status as string} · Suggested max: {env.recommendedMax as number}
            </Text>
            <TextInput
              style={{ backgroundColor: '#1a1a2a', color: '#fff', padding: 12, borderRadius: 8, fontSize: 16, marginBottom: 8 }}
              placeholder="What's on your mind?"
              placeholderTextColor="#666"
              value={dumpText}
              onChangeText={setDumpText}
              onSubmitEditing={doBrainDump}
            />
            <TouchableOpacity onPress={doBrainDump} style={{ backgroundColor: '#22c55e', padding: 12, borderRadius: 8, alignItems: 'center', marginBottom: 16 }}>
              <Text style={{ color: '#fff', fontWeight: '600' }}>That works</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={startListening} style={{ backgroundColor: listening ? '#f87171' : '#2a2a3a', padding: 8, borderRadius: 8, alignItems: 'center', marginBottom: 16, width: 120, alignSelf: 'center' }}>
              <Text style={{ color: '#fff' }}>{listening ? '🎤 Listening...' : '🎤 Voice'}</Text>
            </TouchableOpacity>
            {dumpResult && (
              <View style={{ backgroundColor: '#1a1a2a', padding: 12, borderRadius: 8, marginBottom: 16 }}>
                {dumpResult.structured?.tasks?.map((t: any, i: number) => (
                  <Text key={i} style={{ color: '#ccc', marginBottom: 4 }}>• {t.title}</Text>
                ))}
                {dumpResult.structured?.notes?.map((n: any, i: number) => (
                  <Text key={i} style={{ color: '#666', fontSize: 12, marginBottom: 4 }}>📝 {n.content}</Text>
                ))}
              </View>
            )}
          </ScrollView>
        )}

        {/* Tasks tab */}
        {tab === 'tasks' && (
          <FlatList
            data={tasks.filter((t: any) => t.status !== 'done')}
            keyExtractor={(t: any) => t.id}
            renderItem={({ item: t }) => (
              <View style={{ backgroundColor: '#1a1a2a', padding: 12, borderRadius: 8, marginBottom: 8 }}>
                <Text style={{ color: '#fff', fontSize: 16 }}>{t.title}</Text>
                <Text style={{ color: '#666', fontSize: 12 }}>{t.energy_tag} · {t.spoon_cost} energy</Text>
              </View>
            )}
            ListEmptyComponent={<Text style={{ color: '#666', textAlign: 'center' }}>Nothing yet. Try a brain dump.</Text>}
          />
        )}

        {/* Focus tab */}
        {tab === 'focus' && (
          <ScrollView>
            <Text style={{ fontSize: 20, color: '#fff', marginBottom: 16 }}>What's one thing?</Text>
            {tasks.filter((t: any) => t.status !== 'done').slice(0, 1).map(t => (
              <View key={t.id} style={{ backgroundColor: '#1a1a2a', padding: 16, borderRadius: 8, marginBottom: 16 }}>
                <Text style={{ color: '#fff', fontSize: 18 }}>{t.title}</Text>
              </View>
            ))}
            <TouchableOpacity onPress={loadMenu} style={{ backgroundColor: '#2a2a3a', padding: 12, borderRadius: 8, alignItems: 'center', marginBottom: 16 }}>
              <Text style={{ color: '#fff' }}>🎮 Need a boost?</Text>
            </TouchableOpacity>
            {menu && Object.entries(menu).map(([cat, items]: any) =>
              items?.length > 0 && (
                <View key={cat} style={{ marginBottom: 12 }}>
                  <Text style={{ color: '#888', fontSize: 12, marginBottom: 4 }}>{cat}</Text>
                  {items.map((i: any) => (
                    <Text key={i.id} style={{ color: '#ccc', marginBottom: 2 }}>  {i.name}</Text>
                  ))}
                </View>
              )
            )}
          </ScrollView>
        )}

        {/* Review tab */}
        {tab === 'review' && (
          <ScrollView>
            <Text style={{ fontSize: 20, color: '#fff', marginBottom: 16 }}>Review</Text>
            <Text style={{ color: '#888' }}>Tasks done: {tasks.filter((t: any) => t.status === 'done').length}</Text>
          </ScrollView>
        )}
      </View>
    </SafeAreaView>
  );
}
