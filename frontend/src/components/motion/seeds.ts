import type { MotionProps } from 'framer-motion';

export type MotionRecipe = Pick<
  MotionProps,
  'initial' | 'animate' | 'exit' | 'whileHover' | 'whileTap' | 'transition' | 'layout'
>;

export interface MotionSeed {
  name: string;
  entrance: MotionRecipe;
  exit: MotionRecipe;
  hover: MotionRecipe;
  press: MotionRecipe;
  layout: MotionRecipe;
}

// Snap seed: Sharp, decisive, fast (Linear/Raycast style)
export const snap: MotionSeed = {
  name: 'Snap',
  entrance: {
    initial: { opacity: 0, y: 4 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.14, ease: [0.16, 1, 0.3, 1] },
  },
  exit: {
    initial: { opacity: 1, y: 0 },
    animate: { opacity: 0, y: -4 },
    transition: { duration: 0.1, ease: [0.7, 0, 0.84, 0] },
  },
  hover: {
    whileHover: { y: -1 },
    transition: { duration: 0.12, ease: [0.16, 1, 0.3, 1] },
  },
  press: {
    whileTap: { scale: 0.98 },
    transition: { duration: 0.08, ease: 'easeOut' },
  },
  layout: {
    layout: true,
    transition: { duration: 0.16, ease: [0.16, 1, 0.3, 1] },
  },
};

// Silk seed: Smooth, composed, fluid (Notion/Stripe style)
export const silk: MotionSeed = {
  name: 'Silk',
  entrance: {
    initial: { opacity: 0, scale: 0.98, y: 6 },
    animate: { opacity: 1, scale: 1, y: 0 },
    transition: { duration: 0.22, ease: [0.25, 1, 0.5, 1] },
  },
  exit: {
    initial: { opacity: 1, scale: 1, y: 0 },
    animate: { opacity: 0, scale: 0.98, y: 4 },
    transition: { duration: 0.16, ease: [0.5, 0, 0.75, 0] },
  },
  hover: {
    whileHover: { scale: 1.01 },
    transition: { duration: 0.18, ease: [0.25, 1, 0.5, 1] },
  },
  press: {
    whileTap: { scale: 0.97 },
    transition: { duration: 0.12, ease: 'easeOut' },
  },
  layout: {
    layout: true,
    transition: { duration: 0.22, ease: [0.25, 1, 0.5, 1] },
  },
};

// Spring seed: Tactile, energetic, responsive
export const spring: MotionSeed = {
  name: 'Spring',
  entrance: {
    initial: { opacity: 0, scale: 0.92, y: 8 },
    animate: { opacity: 1, scale: 1, y: 0 },
    transition: { type: 'spring', stiffness: 350, damping: 25 },
  },
  exit: {
    initial: { opacity: 1, scale: 1, y: 0 },
    animate: { opacity: 0, scale: 0.94, y: 6 },
    transition: { duration: 0.12, ease: 'easeIn' },
  },
  hover: {
    whileHover: { scale: 1.02 },
    transition: { type: 'spring', stiffness: 400, damping: 22 },
  },
  press: {
    whileTap: { scale: 0.96 },
    transition: { type: 'spring', stiffness: 600, damping: 20 },
  },
  layout: {
    layout: true,
    transition: { type: 'spring', stiffness: 350, damping: 25 },
  },
};
