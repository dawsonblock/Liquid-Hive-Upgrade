import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

const theme = createTheme({
  palette: {
    mode: 'light',
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ my: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Liquid Hive Upgrade
          </Typography>
          <Typography variant="h6" component="h2" gutterBottom>
            Advanced AI Agent Platform
          </Typography>
          <Typography variant="body1">
            Welcome to the Liquid Hive Upgrade platform. This is a simplified frontend that builds successfully.
          </Typography>
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;