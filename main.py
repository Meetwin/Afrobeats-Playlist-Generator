#!/usr/bin/env python3
"""
YouTube Afrobeats Playlist Generator - Actually Works Version
Creates real playlists with authentic Afrobeats content only
"""

import os
import json
import time
import webbrowser
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

load_dotenv()

class AfrobeatsPlaylistGenerator:
    
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.readonly',
        'https://www.googleapis.com/auth/youtube'
    ]
    
    def __init__(self):
        self.youtube = None
        self.credentials = None
        
        # Stricter criteria for up-and-coming artists
        self.max_subscribers = 250000      # Even smaller artists
        self.max_channel_views = 3000000   # Less established
        self.min_video_views = 5000        # Must have decent traction
        self.max_video_age_days = 45       # Very recent content
        
        # STRICT Afrobeats keywords - only authentic terms
        self.afrobeats_keywords = [
            'afrobeats 2024 nigeria', 'afrobeats 2025 new', 
            'naija afrobeats latest', 'nigeria afrobeats trending',
            'ghana afrobeats new', 'afrobeats hits nigeria',
            'naija new music 2024', 'nigerian artist new song',
            'lagos afrobeats', 'afrobeats underground nigeria',
            'naija upcoming artist', 'nigeria music 2024'
        ]
        
        # REQUIRED Afrobeats indicators (must have at least 2)
        self.required_afrobeats_terms = [
            'afrobeats', 'afrobeat', 'naija', 'nigeria', 'nigerian',
            'ghana', 'ghanaian', 'lagos', 'accra', 'yoruba', 'igbo',
            'amapiano', 'afro beats', 'afro-beats'
        ]
        
        # Strong African music indicators
        self.african_music_terms = [
            'pidgin english', 'yoruba music', 'igbo music', 'hausa music',
            'twi music', 'akan music', 'african music', 'west africa',
            'nigeria music', 'ghana music', 'afro pop', 'afro fusion'
        ]
        
        # Exclude non-Afrobeats content
        self.exclude_terms = [
            'cover', 'remix of', 'karaoke', 'instrumental', 'tutorial',
            'reaction', 'review', 'behind the scenes', 'interview',
            'gospel', 'christian', 'worship', 'highlife', 'juju music',
            'fuji music', 'makossa', 'soukous', 'reggae', 'dancehall'
        ]
        
        self._setup_youtube()
    
    def _setup_youtube(self):
        """Setup YouTube API with proper authentication"""
        try:
            if os.path.exists('token.json'):
                self.credentials = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    print("🔄 Refreshing authentication...")
                    self.credentials.refresh(Request())
                else:
                    print("🔐 First-time authentication...")
                    if not os.path.exists('credentials.json'):
                        print("❌ Need credentials.json file!")
                        print("📝 Get OAuth credentials from Google Cloud Console")
                        print("💡 For now, let's try API key mode...")
                        self._setup_api_key_mode()
                        return
                    
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                
                with open('token.json', 'w') as token:
                    token.write(self.credentials.to_json())
            
            self.youtube = build('youtube', 'v3', credentials=self.credentials)
            print("✅ YouTube API ready with full access!")
            
            # Test if we can actually create playlists
            self._test_playlist_creation()
            
        except Exception as e:
            print(f"⚠️  OAuth failed: {e}")
            print("💡 Trying API key mode...")
            self._setup_api_key_mode()
    
    def _setup_api_key_mode(self):
        """Fallback to API key for discovery only"""
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("❌ No YouTube API key found!")
            print("📝 Add YOUTUBE_API_KEY=your_key to .env file")
            exit(1)
        
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.can_create_playlists = False
        print("✅ YouTube API ready (discovery mode only)")
    
    def _test_playlist_creation(self):
        """Test if we can create playlists"""
        try:
            # Try to list user's playlists
            self.youtube.playlists().list(part='id', mine=True, maxResults=1).execute()
            self.can_create_playlists = True
            print("✅ Playlist creation enabled!")
        except HttpError as e:
            print(f"⚠️  Playlist creation failed: {e}")
            if "youtubeSignupRequired" in str(e):
                print("💡 Go to youtube.com and create a channel first!")
            self.can_create_playlists = False
    
    def is_authentic_afrobeats(self, title, description, channel_title, tags=None):
        """STRICT filtering for authentic Afrobeats content only"""
        if tags is None:
            tags = []
        
        # Combine all text
        all_text = f"{title} {description} {channel_title} {' '.join(tags)}".lower()
        
        # Must NOT contain excluded terms
        for exclude in self.exclude_terms:
            if exclude in all_text:
                return False
        
        # Count Afrobeats indicators
        afrobeats_score = 0
        for term in self.required_afrobeats_terms:
            if term in all_text:
                afrobeats_score += 1
        
        # Count African music indicators
        african_score = 0
        for term in self.african_music_terms:
            if term in all_text:
                african_score += 1
        
        # STRICT requirement: Must have at least 2 Afrobeats terms OR 1 Afrobeats + 1 African
        is_afrobeats = (afrobeats_score >= 2) or (afrobeats_score >= 1 and african_score >= 1)
        
        # Additional checks
        has_music_terms = any(term in all_text for term in ['music', 'song', 'track', 'official', 'video'])
        
        # Debug output for first few videos
        if afrobeats_score > 0:
            print(f"   🔍 Checking: {title[:30]}... | Afrobeats:{afrobeats_score} African:{african_score} Music:{has_music_terms} = {'✅' if is_afrobeats and has_music_terms else '❌'}")
        
        return is_afrobeats and has_music_terms
    
    def search_afrobeats_videos(self):
        """Search with STRICT Afrobeats filtering"""
        print("🔍 Searching for AUTHENTIC Afrobeats content only...")
        afrobeats_videos = []
        
        cutoff_date = datetime.now() - timedelta(days=self.max_video_age_days)
        published_after = cutoff_date.isoformat() + 'Z'
        
        for keyword in self.afrobeats_keywords:
            try:
                print(f"\n   🎯 Searching: {keyword}")
                
                search_response = self.youtube.search().list(
                    q=keyword,
                    part='id,snippet',
                    type='video',
                    videoCategoryId='10',  # Music only
                    order='viewCount',     # Most viewed first
                    maxResults=20,
                    publishedAfter=published_after,
                    regionCode='NG'        # Nigeria focus
                ).execute()
                
                keyword_videos = 0
                for item in search_response['items']:
                    video = {
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'channel_id': item['snippet']['channelId'],
                        'channel_title': item['snippet']['channelTitle'],
                        'published_at': item['snippet']['publishedAt'],
                        'description': item['snippet']['description'],
                        'thumbnail': item['snippet']['thumbnails']['medium']['url']
                    }
                    
                    # STRICT filtering
                    if self.is_authentic_afrobeats(
                        video['title'], 
                        video['description'], 
                        video['channel_title']
                    ):
                        afrobeats_videos.append(video)
                        keyword_videos += 1
                
                print(f"   ✅ Found {keyword_videos} authentic Afrobeats videos")
                time.sleep(0.2)
                
            except HttpError as e:
                print(f"   ❌ Error: {e}")
                continue
        
        # Remove duplicates
        unique_videos = {v['video_id']: v for v in afrobeats_videos}
        total = len(unique_videos)
        print(f"\n✅ Total authentic Afrobeats videos found: {total}")
        
        if total == 0:
            print("❌ No authentic Afrobeats content found!")
            print("💡 Try adjusting search criteria or keywords")
            
        return list(unique_videos.values())
    
    def get_video_and_channel_stats(self, videos):
        """Get detailed stats for filtering"""
        print("📊 Getting video and channel statistics...")
        
        # Get video stats
        video_ids = [v['video_id'] for v in videos]
        video_stats = {}
        
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            try:
                response = self.youtube.videos().list(
                    part='statistics,contentDetails,snippet',
                    id=','.join(batch)
                ).execute()
                
                for video in response['items']:
                    stats = video['statistics']
                    video_stats[video['id']] = {
                        'view_count': int(stats.get('viewCount', 0)),
                        'like_count': int(stats.get('likeCount', 0)),
                        'comment_count': int(stats.get('commentCount', 0)),
                        'duration': video['contentDetails']['duration'],
                        'tags': video['snippet'].get('tags', [])
                    }
                time.sleep(0.1)
            except Exception as e:
                print(f"   Error getting video stats: {e}")
                continue
        
        # Get channel stats
        print("👥 Getting channel statistics...")
        channel_ids = list(set([v['channel_id'] for v in videos]))
        channel_stats = {}
        
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i:i+50]
            try:
                response = self.youtube.channels().list(
                    part='statistics,snippet',
                    id=','.join(batch)
                ).execute()
                
                for channel in response['items']:
                    stats = channel['statistics']
                    snippet = channel['snippet']
                    channel_stats[channel['id']] = {
                        'subscriber_count': int(stats.get('subscriberCount', 0)),
                        'view_count': int(stats.get('viewCount', 0)),
                        'video_count': int(stats.get('videoCount', 0)),
                        'country': snippet.get('country', ''),
                        'description': snippet.get('description', '')
                    }
                time.sleep(0.1)
            except Exception as e:
                print(f"   Error getting channel stats: {e}")
                continue
        
        return video_stats, channel_stats
    
    def filter_up_and_coming_artists(self, videos, video_stats, channel_stats):
        """Filter for up-and-coming artists with double-check for Afrobeats"""
        print("🎯 Filtering for up-and-coming Afrobeats artists...")
        
        filtered = []
        for video in videos:
            vid_id = video['video_id']
            chan_id = video['channel_id']
            
            if vid_id not in video_stats or chan_id not in channel_stats:
                continue
            
            v_stats = video_stats[vid_id]
            c_stats = channel_stats[chan_id]
            
            # Size criteria for up-and-coming
            meets_size_criteria = (
                c_stats['subscriber_count'] <= self.max_subscribers and
                c_stats['view_count'] <= self.max_channel_views and
                v_stats['view_count'] >= self.min_video_views
            )
            
            if not meets_size_criteria:
                continue
            
            # Double-check for Afrobeats with tags
            is_afrobeats = self.is_authentic_afrobeats(
                video['title'],
                video['description'],
                video['channel_title'],
                v_stats.get('tags', [])
            )
            
            if is_afrobeats:
                video.update(v_stats)
                video.update(c_stats)
                filtered.append(video)
                print(f"   ✅ {video['channel_title']}: {video['title'][:40]}... ({video['subscriber_count']:,} subs)")
        
        print(f"\n✅ Found {len(filtered)} up-and-coming Afrobeats artists!")
        return filtered
    
    def create_real_youtube_playlist(self, videos):
        """Create actual YouTube playlist (not Watch Later!)"""
        if not hasattr(self, 'can_create_playlists') or not self.can_create_playlists:
            return self.create_manual_instructions(videos)
        
        if not videos:
            print("❌ No videos to create playlist with")
            return None
        
        # Sort by views
        sorted_videos = sorted(videos, key=lambda x: x['view_count'], reverse=True)
        
        # Create playlist with simple name
        today = datetime.now().strftime('%Y-%m-%d')
        playlist_name = f"Afrobeats Up and Coming {today}"
        
        try:
            print(f"🎵 Creating NEW YouTube playlist: '{playlist_name}'")
            
            # Create the playlist
            playlist_response = self.youtube.playlists().insert(
                part='snippet,status',
                body={
                    'snippet': {
                        'title': playlist_name,
                        'description': f"Up-and-coming Afrobeats artists discovered on {today}. All artists have under {self.max_subscribers:,} subscribers. Authentic Nigerian/Ghanaian music only."
                    },
                    'status': {
                        'privacyStatus': 'public'
                    }
                }
            ).execute()
            
            playlist_id = playlist_response['id']
            playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            
            print(f"✅ NEW PLAYLIST CREATED!")
            print(f"📍 Playlist ID: {playlist_id}")
            print(f"🔗 URL: {playlist_url}")
            
            # Add videos one by one
            print(f"\n📥 Adding {len(sorted_videos)} videos to playlist...")
            added = 0
            
            for i, video in enumerate(sorted_videos[:50]):  # Max 50 videos
                try:
                    self.youtube.playlistItems().insert(
                        part='snippet',
                        body={
                            'snippet': {
                                'playlistId': playlist_id,
                                'position': i,
                                'resourceId': {
                                    'kind': 'youtube#video',
                                    'videoId': video['video_id']
                                }
                            }
                        }
                    ).execute()
                    
                    added += 1
                    print(f"   {added:2d}. ✅ {video['title'][:45]}... ({video['view_count']:,} views)")
                    time.sleep(0.3)  # Slower to avoid issues
                    
                except HttpError as e:
                    print(f"   ❌ Failed to add: {video['title'][:30]}... ({e})")
                    continue
            
            print(f"\n🎉 SUCCESS! Added {added} Afrobeats videos to your playlist!")
            print(f"🔗 Your playlist: {playlist_url}")
            
            return playlist_url
            
        except HttpError as e:
            print(f"❌ Failed to create playlist: {e}")
            return self.create_manual_instructions(videos)
    
    def create_manual_instructions(self, videos):
        """Create manual playlist instructions (not Watch Later!)"""
        print("📝 Creating manual playlist instructions...")
        
        sorted_videos = sorted(videos, key=lambda x: x['view_count'], reverse=True)
        today = datetime.now().strftime('%Y-%m-%d')
        
        instructions = {
            'playlist_name': f"Afrobeats Up and Coming {today}",
            'total_videos': len(sorted_videos),
            'instructions': [
                "1. Go to https://www.youtube.com/",
                "2. Click your profile picture → 'Your channel'",
                "3. Click 'CREATE' button → 'New playlist'",
                f"4. Name it: 'Afrobeats Up and Coming {today}'",
                "5. Set to 'Public'",
                "6. Use the video URLs below to add each song"
            ],
            'videos': []
        }
        
        print(f"\n📋 MANUAL PLAYLIST CREATION GUIDE")
        print(f"{'='*50}")
        print(f"Playlist name: {instructions['playlist_name']}")
        print(f"Total videos: {len(sorted_videos)}")
        print(f"\n📝 Instructions:")
        for instruction in instructions['instructions']:
            print(f"   {instruction}")
        
        print(f"\n🎵 VIDEOS TO ADD:")
        print(f"{'='*50}")
        
        for i, video in enumerate(sorted_videos[:20], 1):
            video_url = f"https://youtube.com/watch?v={video['video_id']}"
            instructions['videos'].append({
                'position': i,
                'title': video['title'],
                'artist': video['channel_title'],
                'url': video_url,
                'views': video['view_count'],
                'subscribers': video['subscriber_count']
            })
            
            print(f"{i:2d}. {video['title'][:40]}...")
            print(f"    🎤 {video['channel_title']} ({video['subscriber_count']:,} subs)")
            print(f"    🔗 {video_url}")
            print()
        
        # Save to file
        with open('afrobeats_manual_playlist.json', 'w', encoding='utf-8') as f:
            json.dump(instructions, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Instructions saved to 'afrobeats_manual_playlist.json'")
        
        # Open YouTube homepage (NOT Watch Later!)
        print(f"🌐 Opening YouTube homepage...")
        webbrowser.open("https://www.youtube.com/")
        
        return "MANUAL_CREATION_GUIDE"
    
    def run(self):
        """Main execution"""
        try:
            print("🎵 AFROBEATS PLAYLIST GENERATOR")
            print("🎯 Finding authentic up-and-coming Afrobeats artists")
            print(f"📏 Criteria: <{self.max_subscribers:,} subs, >{self.min_video_views:,} views, last {self.max_video_age_days} days\n")
            
            # Step 1: Search with strict filtering
            videos = self.search_afrobeats_videos()
            if not videos:
                print("❌ No authentic Afrobeats found. Try adjusting keywords.")
                return
            
            # Step 2: Get stats
            video_stats, channel_stats = self.get_video_and_channel_stats(videos)
            
            # Step 3: Filter for up-and-coming
            filtered_videos = self.filter_up_and_coming_artists(videos, video_stats, channel_stats)
            if not filtered_videos:
                print("❌ No up-and-coming artists found. Try relaxing criteria.")
                return
            
            # Step 4: Create playlist
            result = self.create_real_youtube_playlist(filtered_videos)
            
            if result and result != "MANUAL_CREATION_GUIDE":
                print(f"\n🎉 SUCCESS! Your Afrobeats playlist is ready!")
                print(f"📱 Check your YouTube app → Library → Playlists")
                print(f"🌐 Opening playlist now...")
                webbrowser.open(result)
            else:
                print(f"\n📋 Manual creation guide ready!")
                print(f"📄 Check 'afrobeats_manual_playlist.json' for complete instructions")
            
        except KeyboardInterrupt:
            print("\n⚠️  Cancelled")
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    creator = AfrobeatsPlaylistGenerator()
    creator.run()

if __name__ == "__main__":
    main()