import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Fade,
  Zoom,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Avatar,
  Badge,
  CircularProgress,
  Alert,
  AlertTitle,
} from '@mui/material';
import {
  Memory as MemoryIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  Security as SecurityIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Timeline as TimelineIcon,
  Psychology as PsychologyIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'good' | 'warning' | 'error';
  trend: 'up' | 'down' | 'stable';
  icon: React.ReactNode;
}

interface AlertItem {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  resolved: boolean;
}

const ModernDashboard: React.FC = () => {
  const theme = useTheme();
  const [metrics, setMetrics] = useState<SystemMetric[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      setMetrics([
        {
          name: 'Consciousness Level (Φ)',
          value: 0.8472,
          unit: '',
          status: 'good',
          trend: 'up',
          icon: <PsychologyIcon />,
        },
        {
          name: 'Memory Usage',
          value: 68.5,
          unit: '%',
          status: 'warning',
          trend: 'up',
          icon: <MemoryIcon />,
        },
        {
          name: 'Processing Speed',
          value: 2.4,
          unit: 'GHz',
          status: 'good',
          trend: 'stable',
          icon: <SpeedIcon />,
        },
        {
          name: 'Storage',
          value: 45.2,
          unit: '%',
          status: 'good',
          trend: 'down',
          icon: <StorageIcon />,
        },
        {
          name: 'Security Score',
          value: 94.8,
          unit: '%',
          status: 'good',
          trend: 'up',
          icon: <SecurityIcon />,
        },
        {
          name: 'Learning Rate',
          value: 0.0234,
          unit: '/sec',
          status: 'good',
          trend: 'up',
          icon: <TrendingUpIcon />,
        },
      ]);

      setAlerts([
        {
          id: '1',
          type: 'info',
          title: 'System Update Available',
          message: 'New version 2.1.0 is ready for installation',
          timestamp: new Date(Date.now() - 1000 * 60 * 30),
          resolved: false,
        },
        {
          id: '2',
          type: 'warning',
          title: 'Memory Usage High',
          message: 'Memory usage is approaching 70% threshold',
          timestamp: new Date(Date.now() - 1000 * 60 * 15),
          resolved: false,
        },
        {
          id: '3',
          type: 'success',
          title: 'Backup Completed',
          message: 'System backup completed successfully',
          timestamp: new Date(Date.now() - 1000 * 60 * 60),
          resolved: true,
        },
      ]);

      setLastUpdate(new Date());
    } catch (error) {
      // TODO: Replace with proper error handling
        console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return theme.palette.success.main;
      case 'warning': return theme.palette.warning.main;
      case 'error': return theme.palette.error.main;
      default: return theme.palette.grey[500];
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return '↗';
      case 'down': return '↘';
      case 'stable': return '→';
      default: return '→';
    }
  };

  const MetricCard: React.FC<{ metric: SystemMetric }> = ({ metric }) => (
    <Zoom in timeout={300}>
      <Card
        sx={{
          height: '100%',
          background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.grey[50]} 100%)`,
          border: `1px solid ${theme.palette.divider}`,
          transition: 'all 0.3s ease',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: theme.shadows[8],
          },
        }}
      >
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar
              sx={{
                bgcolor: getStatusColor(metric.status),
                mr: 2,
                width: 48,
                height: 48,
              }}
            >
              {metric.icon}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" color="textPrimary" gutterBottom>
                {metric.name}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h4" color="textPrimary">
                  {metric.value.toFixed(metric.unit === '%' ? 1 : 4)}
                </Typography>
                <Typography variant="h6" color="textSecondary">
                  {metric.unit}
                </Typography>
                <Chip
                  size="small"
                  label={getTrendIcon(metric.trend)}
                  color={metric.trend === 'up' ? 'success' : metric.trend === 'down' ? 'error' : 'default'}
                  variant="outlined"
                />
              </Box>
            </Box>
          </Box>

          <LinearProgress
            variant="determinate"
            value={metric.unit === '%' ? metric.value : Math.min(metric.value * 20, 100)}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: theme.palette.grey[200],
              '& .MuiLinearProgress-bar': {
                backgroundColor: getStatusColor(metric.status),
                borderRadius: 4,
              },
            }}
          />
        </CardContent>
      </Card>
    </Zoom>
  );

  const AlertCard: React.FC<{ alert: AlertItem }> = ({ alert }) => (
    <Fade in timeout={300}>
      <Alert
        severity={alert.type}
        sx={{
          mb: 2,
          '& .MuiAlert-message': {
            width: '100%',
          },
        }}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption" color="textSecondary">
              {alert.timestamp.toLocaleTimeString()}
            </Typography>
            {!alert.resolved && (
              <IconButton size="small" color="inherit">
                <CheckCircleIcon fontSize="small" />
              </IconButton>
            )}
          </Box>
        }
      >
        <AlertTitle>{alert.title}</AlertTitle>
        {alert.message}
      </Alert>
    </Fade>
  );

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AutoAwesomeIcon color="primary" />
            Capsule Brain Dashboard
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh">
            <IconButton onClick={loadDashboardData} disabled={isLoading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Settings">
            <IconButton>
              <SettingsIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Notifications">
            <IconButton>
              <Badge badgeContent={alerts.filter(a => !a.resolved).length} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {isLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Metrics Grid */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {metrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={4} key={index}>
            <MetricCard metric={metric} />
          </Grid>
        ))}
      </Grid>

      {/* Alerts and Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <WarningIcon color="warning" />
                System Alerts
              </Typography>
              <Divider sx={{ mb: 2 }} />
              {alerts.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 2 }} />
                  <Typography variant="h6" color="textSecondary">
                    All systems operational
                  </Typography>
                </Box>
              ) : (
                alerts.map((alert) => (
                  <AlertCard key={alert.id} alert={alert} />
                ))
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TimelineIcon color="primary" />
                Recent Activity
              </Typography>
              <Divider sx={{ mb: 2 }} />
              <List>
                <ListItem>
                  <ListItemIcon>
                    <Avatar sx={{ bgcolor: 'success.main', width: 32, height: 32 }}>
                      <CheckCircleIcon fontSize="small" />
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary="System Check Completed"
                    secondary="2 minutes ago"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Avatar sx={{ bgcolor: 'info.main', width: 32, height: 32 }}>
                      <PsychologyIcon fontSize="small" />
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary="Consciousness Level Updated"
                    secondary="5 minutes ago"
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <Avatar sx={{ bgcolor: 'warning.main', width: 32, height: 32 }}>
                      <WarningIcon fontSize="small" />
                    </Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary="Memory Usage Alert"
                    secondary="15 minutes ago"
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ModernDashboard;
