import type { Meta, StoryObj } from '@storybook/react';
import { ThemeProvider, CssBaseline, Box, Stack, Typography, Divider } from '@mui/material';
import theme from '../theme';

const meta: Meta = {
  title: 'Foundation/Typography',
  parameters: {
    layout: 'centered',
  },
};

export default meta;

type Story = StoryObj;

const sampleText = 'The quick brown fox jumps over the lazy dog 1234567890';

export const Overview: Story = {
  render: () => (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box padding={4} minWidth={420} maxWidth={640}>
        <Stack spacing={3} divider={<Divider flexItem />}> 
          <Stack spacing={0.5}>
            <Typography variant="overline" color="text.secondary">
              Display
            </Typography>
            <Typography variant="h2" fontWeight={500} letterSpacing="-0.015em">
              {sampleText}
            </Typography>
          </Stack>
          <Stack spacing={1}>
            <Typography variant="overline" color="text.secondary">
              Headings
            </Typography>
            <Typography variant="h1">H1 · {sampleText}</Typography>
            <Typography variant="h2">H2 · {sampleText}</Typography>
            <Typography variant="h3">H3 · {sampleText}</Typography>
            <Typography variant="h4">H4 · {sampleText}</Typography>
            <Typography variant="h5">H5 · {sampleText}</Typography>
            <Typography variant="h6">H6 · {sampleText}</Typography>
          </Stack>
          <Stack spacing={1}>
            <Typography variant="overline" color="text.secondary">
              Body
            </Typography>
            <Typography variant="subtitle1">Subtitle · {sampleText}</Typography>
            <Typography variant="body1">Body 1 · {sampleText}</Typography>
            <Typography variant="body2">Body 2 · {sampleText}</Typography>
            <Typography variant="caption">Caption · {sampleText}</Typography>
          </Stack>
        </Stack>
      </Box>
    </ThemeProvider>
  ),
};
