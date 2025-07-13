// app/page.js or app/page.tsx
import AudioRecorder from '@/components/AudioRecorder' // 确保路径正确

export default function Home() {
  return (
    <main style={{ padding: '2rem' }}>
      <h1>Next.js Microphone Recorder</h1>
      <p>A simple audio recorder using browser APIs.</p>
      <AudioRecorder />
    </main>
  )
}
