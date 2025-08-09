import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { Alert, AlertDescription } from './components/ui/alert';
import { 
  Bot, 
  FileText, 
  Video, 
  Users, 
  BarChart3,
  Zap,
  Shield,
  Star,
  Search,
  Download,
  Eye
} from 'lucide-react';
import './App.css';

function App() {
  const [filename, setFilename] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total_users: 0, total_analyses: 0 });
  const [error, setError] = useState('');

  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
  };

  const analyzeFile = async () => {
    if (!filename.trim()) {
      setError('Please enter a filename');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      const response = await fetch(`${backendUrl}/api/analyze-file?filename=${encodeURIComponent(filename)}`);
      if (response.ok) {
        const data = await response.json();
        setAnalysis(data);
      } else {
        throw new Error('Analysis failed');
      }
    } catch (error) {
      setError('Failed to analyze file. Please try again.');
      console.error('Analysis error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      analyzeFile();
    }
  };

  const sampleFiles = [
    "Avengers.Endgame.2019.2160p.BluRay.x265.10bit.HDR.TrueHD.7.1.Atmos-SWTYBLZ.mkv",
    "The.Matrix.1999.1080p.WEB-DL.DD5.1.H.264-FGT.mp4",
    "Breaking.Bad.S01E01.720p.HDTV.x264-CTU.avi",
    "Dune.2021.IMAX.WEBRip.1080p.x264.AAC.mkv"
  ];

  const getQualityColor = (quality) => {
    const qualityColors = {
      'BluRay': 'bg-violet-100 text-violet-800 border-violet-200',
      'WEB-DL': 'bg-blue-100 text-blue-800 border-blue-200',
      'WEBRip': 'bg-cyan-100 text-cyan-800 border-cyan-200',
      'HDTV': 'bg-green-100 text-green-800 border-green-200',
      'DVDRip': 'bg-yellow-100 text-yellow-800 border-yellow-200',
      'CAM': 'bg-red-100 text-red-800 border-red-200'
    };
    return qualityColors[quality] || 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const getFormatIcon = (format) => {
    switch(format?.toLowerCase()) {
      case 'mkv': return '🎬';
      case 'mp4': return '📺';
      case 'avi': return '🎥';
      case 'webm': return '🌐';
      default: return '📁';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-lg border-b border-slate-200/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2 rounded-xl">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-800">Telegram File Analyzer</h1>
                <p className="text-sm text-slate-600">Advanced metadata detection bot</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant="secondary" className="bg-green-100 text-green-800">
                <Users className="w-3 h-3 mr-1" />
                {stats.total_users} Users
              </Badge>
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                <BarChart3 className="w-3 h-3 mr-1" />
                {stats.total_analyses} Analyses
              </Badge>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
        
        {/* Hero Section */}
        <div className="text-center space-y-6">
          <div className="space-y-4">
            <h2 className="text-4xl font-bold text-slate-800 leading-tight">
              Analyze Any <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Telegram File</span>
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Get detailed metadata about video files including quality, resolution, codecs, and source platform detection
            </p>
          </div>

          {/* Quick Features */}
          <div className="flex flex-wrap justify-center gap-4 pt-2">
            {[
              { icon: Video, label: 'Video Analysis', color: 'text-red-600' },
              { icon: Eye, label: 'Quality Detection', color: 'text-blue-600' },
              { icon: Shield, label: 'Codec Identification', color: 'text-green-600' },
              { icon: Zap, label: 'Instant Results', color: 'text-purple-600' }
            ].map((feature, index) => (
              <div key={index} className="flex items-center space-x-2 bg-white/60 px-3 py-2 rounded-full">
                <feature.icon className={`w-4 h-4 ${feature.color}`} />
                <span className="text-sm font-medium text-slate-700">{feature.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Analysis Tool */}
        <Card className="bg-white/80 backdrop-blur-sm border-slate-200/60 shadow-xl">
          <CardHeader className="text-center pb-4">
            <CardTitle className="flex items-center justify-center space-x-2 text-xl">
              <Search className="w-5 h-5 text-blue-600" />
              <span>File Analysis Tool</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            
            {/* Input Section */}
            <div className="space-y-4">
              <div className="flex space-x-3">
                <div className="flex-1">
                  <Input
                    placeholder="Enter filename (e.g., Movie.2023.1080p.BluRay.x264.mkv)"
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    onKeyPress={handleKeyPress}
                    className="h-12 text-base bg-white/80 border-slate-300"
                  />
                </div>
                <Button 
                  onClick={analyzeFile} 
                  disabled={loading}
                  className="h-12 px-8 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium shadow-lg"
                >
                  {loading ? (
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      <span>Analyzing...</span>
                    </div>
                  ) : (
                    <div className="flex items-center space-x-2">
                      <Search className="w-4 h-4" />
                      <span>Analyze</span>
                    </div>
                  )}
                </Button>
              </div>

              {/* Sample Files */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-600">Try these sample files:</p>
                <div className="flex flex-wrap gap-2">
                  {sampleFiles.map((sample, index) => (
                    <button
                      key={index}
                      onClick={() => setFilename(sample)}
                      className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-md transition-colors duration-200 border border-slate-200"
                    >
                      {sample.split('.')[0]}...
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <Alert className="border-red-200 bg-red-50">
                <AlertDescription className="text-red-700">
                  {error}
                </AlertDescription>
              </Alert>
            )}

            {/* Analysis Results */}
            {analysis && (
              <div className="space-y-6 pt-6 border-t border-slate-200/60">
                <div className="flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-slate-800">Analysis Results</h3>
                </div>

                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-100">
                  
                  {/* Filename */}
                  <div className="space-y-4">
                    <div className="bg-white/60 rounded-lg p-4">
                      <p className="text-sm font-medium text-slate-600 mb-1">Filename</p>
                      <p className="font-mono text-sm text-slate-800 break-all bg-slate-100 p-2 rounded">
                        {analysis.filename}
                      </p>
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      
                      {/* File Type */}
                      <div className="bg-white/60 rounded-lg p-4">
                        <p className="text-sm font-medium text-slate-600 mb-2">File Format</p>
                        <div className="flex items-center space-x-2">
                          <span className="text-2xl">{getFormatIcon(analysis.file_type)}</span>
                          <Badge className="bg-slate-100 text-slate-800 border-slate-200">
                            {analysis.file_type}
                          </Badge>
                        </div>
                      </div>

                      {/* Quality */}
                      {analysis.quality && (
                        <div className="bg-white/60 rounded-lg p-4">
                          <p className="text-sm font-medium text-slate-600 mb-2">Quality</p>
                          <Badge className={getQualityColor(analysis.quality)}>
                            <Star className="w-3 h-3 mr-1" />
                            {analysis.quality}
                          </Badge>
                        </div>
                      )}

                      {/* Resolution */}
                      {analysis.resolution && (
                        <div className="bg-white/60 rounded-lg p-4">
                          <p className="text-sm font-medium text-slate-600 mb-2">Resolution</p>
                          <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">
                            📺 {analysis.resolution}
                          </Badge>
                        </div>
                      )}

                      {/* Video Codec */}
                      {analysis.codec && (
                        <div className="bg-white/60 rounded-lg p-4">
                          <p className="text-sm font-medium text-slate-600 mb-2">Video Codec</p>
                          <Badge className="bg-orange-100 text-orange-800 border-orange-200">
                            🎥 {analysis.codec}
                          </Badge>
                        </div>
                      )}

                      {/* Audio Codec */}
                      {analysis.audio_codec && (
                        <div className="bg-white/60 rounded-lg p-4">
                          <p className="text-sm font-medium text-slate-600 mb-2">Audio Codec</p>
                          <Badge className="bg-pink-100 text-pink-800 border-pink-200">
                            🔊 {analysis.audio_codec}
                          </Badge>
                        </div>
                      )}

                      {/* Source */}
                      {analysis.source && (
                        <div className="bg-white/60 rounded-lg p-4">
                          <p className="text-sm font-medium text-slate-600 mb-2">Source Platform</p>
                          <Badge className="bg-purple-100 text-purple-800 border-purple-200">
                            📺 {analysis.source}
                          </Badge>
                        </div>
                      )}

                      {/* Language */}
                      {analysis.language && (
                        <div className="bg-white/60 rounded-lg p-4">
                          <p className="text-sm font-medium text-slate-600 mb-2">Language</p>
                          <Badge className="bg-cyan-100 text-cyan-800 border-cyan-200">
                            🌐 {analysis.language}
                          </Badge>
                        </div>
                      )}
                    </div>

                    {/* Additional Details */}
                    {analysis.format_details && Object.keys(analysis.format_details).some(key => analysis.format_details[key]) && (
                      <div className="bg-white/60 rounded-lg p-4 space-y-3">
                        <p className="text-sm font-medium text-slate-600">Additional Information</p>
                        <div className="flex flex-wrap gap-2">
                          {analysis.format_details.year && (
                            <Badge variant="secondary">📅 {analysis.format_details.year}</Badge>
                          )}
                          {analysis.format_details.season_episode && (
                            <Badge variant="secondary">📺 {analysis.format_details.season_episode}</Badge>
                          )}
                          {analysis.format_details.has_subtitles && (
                            <Badge variant="secondary">💬 Subtitles</Badge>
                          )}
                          {analysis.format_details.has_multiple_audio && (
                            <Badge variant="secondary">🎵 Multi-Audio</Badge>
                          )}
                          {analysis.format_details.is_3d && (
                            <Badge variant="secondary">🕶️ 3D</Badge>
                          )}
                          {analysis.format_details.is_hdr && (
                            <Badge variant="secondary">✨ HDR</Badge>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Telegram Bot Info */}
        <Card className="bg-gradient-to-br from-indigo-50 to-purple-50 border-indigo-200/60">
          <CardContent className="p-8 text-center space-y-6">
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="bg-gradient-to-br from-indigo-600 to-purple-600 p-4 rounded-2xl">
                  <Bot className="w-8 h-8 text-white" />
                </div>
              </div>
              
              <div>
                <h3 className="text-2xl font-bold text-slate-800 mb-2">Use Our Telegram Bot</h3>
                <p className="text-slate-600 max-w-md mx-auto">
                  Forward any file directly to our Telegram bot for instant analysis
                </p>
              </div>

              <div className="bg-white/60 rounded-lg p-4 inline-block">
                <p className="text-sm font-medium text-slate-600 mb-2">Bot Commands:</p>
                <div className="space-y-1 text-sm font-mono text-left">
                  <div><span className="text-indigo-600">/start</span> - Get started</div>
                  <div><span className="text-indigo-600">/analyze filename</span> - Analyze specific file</div>
                  <div><span className="text-indigo-600">/stats</span> - View your stats</div>
                </div>
              </div>

              <Button 
                className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white px-8 py-3 rounded-xl shadow-lg"
                onClick={() => window.open('https://t.me/your_bot_username', '_blank')}
              >
                <Download className="w-4 h-4 mr-2" />
                Open Telegram Bot
              </Button>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* Footer */}
      <footer className="bg-white/80 backdrop-blur-lg border-t border-slate-200/60 mt-16">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center">
          <p className="text-slate-600">
            Built with ❤️ for the community • Advanced file metadata analysis
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;