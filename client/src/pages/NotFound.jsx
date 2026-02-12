import { Link } from 'react-router-dom';

const NotFound = () => {
    return (
        <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'black', color: '#ff3366' }}>
            <h1 style={{ fontSize: '10rem', fontFamily: 'monospace', margin: 0 }}>404</h1>
            <p style={{ fontSize: '2rem', fontFamily: 'monospace' }}>SECTOR LOST</p>
            <Link to="/" style={{ marginTop: '2rem', color: '#fff', border: '1px solid #fff', padding: '1rem' }}>RETURN TO SAFE ZONE</Link>
        </div>
    );
};

export default NotFound;
