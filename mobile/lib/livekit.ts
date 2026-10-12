// LiveKit room transport (doc §3.2). The app publishes its mic audio into a
// per-drive room; the backend room agent subscribes, runs the pipeline, and
// publishes the TTS answer back as an audio track. Control events (transcript,
// response text, saved_place) arrive as LiveKit data packets.
import {
  Room,
  RoomEvent,
  Track,
  type RemoteTrack,
  type RemoteParticipant,
} from '@livekit/react-native';

export interface RoomCallbacks {
  onData: (msg: any) => void; // transcript / response / done / error / proactive
  onAgentTrack: (track: RemoteTrack) => void; // TTS audio to play
}

export async function joinRoom(
  url: string,
  token: string,
  cb: RoomCallbacks,
): Promise<Room> {
  const room = new Room({ adaptiveStream: true });

  room.on(RoomEvent.DataReceived, (payload: Uint8Array) => {
    try {
      cb.onData(JSON.parse(new TextDecoder().decode(payload)));
    } catch {
      /* ignore non-JSON data */
    }
  });

  room.on(
    RoomEvent.TrackSubscribed,
    (track: RemoteTrack, _pub, _participant: RemoteParticipant) => {
      if (track.kind === Track.Kind.Audio) cb.onAgentTrack(track);
    },
  );

  await room.connect(url, token);
  // Publish mic — this is the audio the backend transcribes.
  await room.localParticipant.setMicrophoneEnabled(true);
  return room;
}

export async function leaveRoom(room: Room | null): Promise<void> {
  await room?.disconnect();
}
