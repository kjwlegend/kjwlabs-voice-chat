// components/AudioRecorder.tsx
'use client'

import { useState, useRef } from 'react'

const mimeType = 'audio/webm'

const AudioRecorder = () => {
  const [permission, setPermission] = useState(false)
  const [stream, setStream] = useState<MediaStream | null>(null)
  const mediaRecorder = useRef<MediaRecorder | null>(null)
  const [recordingStatus, setRecordingStatus] = useState<
    'recording' | 'inactive'
  >('inactive')
  const [audioChunks, setAudioChunks] = useState<Blob[]>([])
  const [audio, setAudio] = useState<string | null>(null)

  const getMicrophonePermission = async () => {
    if ('MediaRecorder' in window) {
      try {
        const streamData = await navigator.mediaDevices.getUserMedia({
          audio: true,
          video: false,
        })
        setPermission(true)
        setStream(streamData)
      } catch (err: any) {
        alert(err.message)
      }
    } else {
      alert('The MediaRecorder API is not supported in your browser.')
    }
  }

  const startRecording = async () => {
    if (stream === null) return

    setRecordingStatus('recording')
    const media = new MediaRecorder(stream, { mimeType })
    mediaRecorder.current = media
    mediaRecorder.current.start()

    let localAudioChunks: Blob[] = []
    mediaRecorder.current.ondataavailable = (event) => {
      if (typeof event.data === 'undefined') return
      if (event.data.size === 0) return
      localAudioChunks.push(event.data)
    }
    setAudioChunks(localAudioChunks)
  }

  const stopRecording = () => {
    if (mediaRecorder.current === null) return

    setRecordingStatus('inactive')
    mediaRecorder.current.stop()
    mediaRecorder.current.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: mimeType })
      const audioUrl = URL.createObjectURL(audioBlob)
      setAudio(audioUrl)
      setAudioChunks([])
    }
  }

  return (
    <div>
      <h2>Audio Recorder</h2>
      <main>
        <div
          className="audio-controls"
          style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}
        >
          {!permission ? (
            <button onClick={getMicrophonePermission} type="button">
              Get Microphone
            </button>
          ) : null}
          {permission && recordingStatus === 'inactive' ? (
            <button onClick={startRecording} type="button">
              Start Recording
            </button>
          ) : null}
          {recordingStatus === 'recording' ? (
            <button onClick={stopRecording} type="button">
              Stop Recording
            </button>
          ) : null}
        </div>
        {audio ? (
          <div className="audio-container">
            <audio src={audio} controls></audio>
            <br />
            <a download="recording.webm" href={audio}>
              Download Recording
            </a>
          </div>
        ) : null}
      </main>
    </div>
  )
}

export default AudioRecorder
