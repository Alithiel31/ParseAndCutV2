import { NavLink } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="site-footer">
      <nav aria-label="Informations légales">
        <NavLink to="/mentions-legales">Mentions légales</NavLink>
        <span aria-hidden="true">·</span>
        <NavLink to="/politique-de-confidentialite">Confidentialité</NavLink>
        <span aria-hidden="true">·</span>
        <NavLink to="/cgu">CGU</NavLink>
      </nav>
      <p>Service gratuit et sans compte — aucun fichier n'est conservé.</p>
    </footer>
  );
}
