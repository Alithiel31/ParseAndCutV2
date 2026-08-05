interface UpdateBannerProps {
  onUpdate: () => void;
  onDismiss: () => void;
}

export default function UpdateBanner({ onUpdate, onDismiss }: UpdateBannerProps) {
  return (
    <div className="update-banner">
      <span>🔄 Une nouvelle version est disponible.</span>
      <button className="btn-secondary" onClick={onUpdate}>
        Mettre à jour
      </button>
      <button className="btn-secondary" onClick={onDismiss}>
        Plus tard
      </button>
    </div>
  );
}
