// Components.d.ts — the complete catalog of the 11 component(s) in
// Components.bundle.js. READ THIS FILE BEFORE USING THE BUNDLE: component
// names are derived from Figma layer names (sanitized to PascalCase,
// deduplicated) and may differ from what the design calls them — the
// "figma layer" comment above each interface maps them back.
// After the bundle <script> loads, every component is a window global
// (e.g. window.CTA) and usable directly in JSX.
import * as React from 'react';

// figma layer: "CTA" (node 3:135)
export interface CTAProps {
  className?: string;
  style?: React.CSSProperties;
  property1?: "default" | "variant2";
  /** Text content; defaults to "GRAB BASICS SET NOW". */
  text1?: string;
}

// figma layer: "Component 1" (node 3:195)
export interface Component1Props {
  className?: string;
  style?: React.CSSProperties;
  /** Text content; defaults to "GET CLEAR SKIN NOW". */
  text1?: string;
}

// figma layer: "Footer" (node 3:109)
export interface FooterProps {
  className?: string;
  style?: React.CSSProperties;
  /** Text content; defaults to "SHOP". */
  text1?: string;
  /** Text content; defaults to "JOIN THE FAM". */
  text2?: string;
  /** Text content; defaults to "FAQ". */
  text3?: string;
  /** Text content; defaults to "Brand B LLC, 100 Example St, Example City, ST 00000". */
  text4?: string;
}

// figma layer: "Header" (node 3:92)
export interface HeaderProps {
  className?: string;
  style?: React.CSSProperties;
}

// figma layer: "Icons" (node 281:721)
export interface IconsProps {
  className?: string;
  style?: React.CSSProperties;
  icons?: "right" | "x";
}

// figma layer: "Link CTA 1" (node 1062:12271)
export interface LinkCTA1Props {
  className?: string;
  style?: React.CSSProperties;
  property1?: "default" | "hover";
  /** Text content; defaults to "VIEW ALL". */
  text1?: string;
}

// figma layer: "Link CTA 2" (node 1062:12285)
export interface LinkCTA2Props {
  className?: string;
  style?: React.CSSProperties;
  property1?: "default" | "hover";
  /** Text content; defaults to "READ MORE". */
  text1?: string;
}

// figma layer: "Link CTA 3" (node 1062:12299)
export interface LinkCTA3Props {
  className?: string;
  style?: React.CSSProperties;
  property1?: "default" | "hover";
  /** Text content; defaults to "LOAD MORE". */
  text1?: string;
}

// figma layer: "Nav" (node 3:95)
export interface NavProps {
  className?: string;
  style?: React.CSSProperties;
  /** Text content; defaults to "Shop". */
  text1?: string;
  /** Text content; defaults to "results". */
  text2?: string;
  /** Text content; defaults to "plan". */
  text3?: string;
  /** Text content; defaults to "Vision". */
  text4?: string;
}

// figma layer: "Preheader" (node 3:90)
export interface PreheaderProps {
  className?: string;
  style?: React.CSSProperties;
  /** Text content; defaults to "NEW RELEASE: TREAT YOUR FACE LIKE ROYALTY WITH THE KING SET". */
  text1?: string;
}

// figma layer: "Preheader - Header" (node 3:105)
export interface PreheaderHeaderProps {
  className?: string;
  style?: React.CSSProperties;
}

declare const CTA: React.FC<CTAProps>;
declare const Component1: React.FC<Component1Props>;
declare const Footer: React.FC<FooterProps>;
declare const Header: React.FC<HeaderProps>;
declare const Icons: React.FC<IconsProps>;
declare const LinkCTA1: React.FC<LinkCTA1Props>;
declare const LinkCTA2: React.FC<LinkCTA2Props>;
declare const LinkCTA3: React.FC<LinkCTA3Props>;
declare const Nav: React.FC<NavProps>;
declare const Preheader: React.FC<PreheaderProps>;
declare const PreheaderHeader: React.FC<PreheaderHeaderProps>;
declare global {
  interface Window {
    CTA: React.FC<CTAProps>;
    Component1: React.FC<Component1Props>;
    Footer: React.FC<FooterProps>;
    Header: React.FC<HeaderProps>;
    Icons: React.FC<IconsProps>;
    LinkCTA1: React.FC<LinkCTA1Props>;
    LinkCTA2: React.FC<LinkCTA2Props>;
    LinkCTA3: React.FC<LinkCTA3Props>;
    Nav: React.FC<NavProps>;
    Preheader: React.FC<PreheaderProps>;
    PreheaderHeader: React.FC<PreheaderHeaderProps>;
  }
}
