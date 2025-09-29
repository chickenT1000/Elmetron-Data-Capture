import { createTheme } from '@mui/material/styles';
import tokens from '../tokens.json';

const fontFamilyBase = tokens.typography.fontFamily.base;
const radii = tokens.radii;
const palette = tokens.colors;
const typeScale = tokens.typography.scale;
const spacing = tokens.spacing;

const buildTypographyVariant = (variantKey: keyof typeof typeScale) => {
  const variant = typeScale[variantKey];
  return {
    fontSize: variant.size,
    lineHeight: variant.lineHeight,
    fontWeight: variant.weight,
    letterSpacing: variant.tracking ?? '0em',
  };
};

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      light: palette.primary.light,
      main: palette.primary.main,
      dark: palette.primary.dark,
      contrastText: palette.primary.on,
    },
    secondary: {
      light: palette.secondary.light,
      main: palette.secondary.main,
      dark: palette.secondary.dark,
      contrastText: palette.secondary.on,
    },
    error: {
      light: palette.error.light,
      main: palette.error.main,
      dark: palette.error.dark,
      contrastText: palette.error.on,
    },
    background: {
      default: palette.background.default,
      paper: palette.background.surface,
    },
    success: {
      light: palette.success.light,
      main: palette.success.main,
      dark: palette.success.dark,
      contrastText: palette.success.on,
    },
    warning: {
      light: palette.warning.light,
      main: palette.warning.main,
      dark: palette.warning.dark,
      contrastText: palette.warning.on,
    },
    info: {
      light: palette.info.light,
      main: palette.info.main,
      dark: palette.info.dark,
      contrastText: palette.info.on,
    },
    text: {
      primary: palette.text.primary,
      secondary: palette.text.secondary,
      disabled: palette.text.muted,
    },
    divider: palette.border.subtle,
  },
  typography: {
    fontFamily: fontFamilyBase,
    h1: buildTypographyVariant('h1'),
    h2: buildTypographyVariant('h2'),
    h3: buildTypographyVariant('h3'),
    h4: buildTypographyVariant('h4'),
    h5: buildTypographyVariant('subtitle'),
    h6: { ...buildTypographyVariant('body'), fontWeight: 600 },
    subtitle1: buildTypographyVariant('subtitle'),
    body1: buildTypographyVariant('body'),
    body2: buildTypographyVariant('body-compact'),
    caption: buildTypographyVariant('caption'),
  },
  components: {
    MuiButton: {
      defaultProps: {
        variant: 'contained',
      },
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: radii.md,
          paddingInline: spacing.md,
          paddingBlock: spacing.xs,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: radii.lg,
          boxShadow: `0 6px 12px rgba(10, 61, 98, 0.08)`,
          border: `1px solid ${palette.border.subtle}`,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: radii.sm,
          fontWeight: 600,
          letterSpacing: '0.01em',
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: radii.sm,
          backgroundColor: palette.neutral[800],
          fontSize: typeScale['body-compact'].size,
        },
      },
    },
  },
});

export default theme;
