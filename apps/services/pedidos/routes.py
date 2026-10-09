"""
pedidos/routes.py
Rutas del microservicio de Pedidos (puerto 5003).
Administra pedidos, líneas de pedido, transacciones atómicas de stock,
coordinación temporal en Redis (order:pending:<order_id>) e invalidación de catálogo.
"""
import sys, os
_curr = os.path.abspath(__file__)
for _ in range(4):
    _curr = os.path.dirname(_curr)
    _cand = os.path.join(_curr, 'apps', 'services')
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)
    if os.path.isdir(os.path.join(_curr, 'common')) and _curr not in sys.path:
        sys.path.insert(0, _curr)

from decimal import Decimal
from flask import Blueprint, request, g
import psycopg.rows

from common import (
    get_connection,
    make_response_format,
    jwt_required,
    roles_required,
    redis_client,
    config
)

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')


# -----------------------------------------------------------------
# GET /orders -- LISTAR PEDIDOS
# -----------------------------------------------------------------
@orders_bp.route('', methods=['GET'])
@jwt_required()
def list_orders():
    """
    Lista pedidos.
    Si el rol es 'admin', devuelve todos los pedidos.
    Si el rol es 'user', devuelve únicamente los pedidos del usuario autenticado.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                if role == 'admin':
                    cur.execute(
                        """SELECT o.id, o.user_id, u.username, u.email,
                                  o.status, o.subtotal, o.total,
                                  o.created_at, o.updated_at
                             FROM orders o
                             JOIN users u ON u.id = o.user_id
                            ORDER BY o.id DESC"""
                    )
                else:
                    cur.execute(
                        """SELECT id, user_id, status, subtotal, total, created_at, updated_at
                             FROM orders
                            WHERE user_id = %s
                            ORDER BY id DESC""",
                        (user_id,)
                    )
                orders = cur.fetchall()

        return make_response_format({
            'status': 'success',
            'orders': orders,
            'count': len(orders)
        }, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# GET /orders/<id> -- DETALLE DE PEDIDO CON ITEMS
# -----------------------------------------------------------------
@orders_bp.route('/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Consulta detalles de un pedido y sus líneas de productos (order_items)."""
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute(
                    """SELECT id, user_id, status, subtotal, total, created_at, updated_at
                         FROM orders WHERE id = %s""",
                    (order_id,)
                )
                order = cur.fetchone()

                if not order:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pedido con ID {order_id} no encontrado.'
                    }, 404, request)

                # Validar autorización
                if role != 'admin' and order['user_id'] != user_id:
                    return make_response_format({
                        'status': 'error',
                        'message': 'Acceso denegado: Este pedido no pertenece a su usuario.'
                    }, 403, request)

                # Obtener líneas del pedido
                cur.execute(
                    """SELECT id, book_id, title_snapshot, unit_price, quantity, line_total
                         FROM order_items
                        WHERE order_id = %s
                        ORDER BY id ASC""",
                    (order_id,)
                )
                items = cur.fetchall()
                order['items'] = items

        return make_response_format({'status': 'success', 'order': order}, 200, request)
    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# POST /orders -- CREAR PEDIDO (TRANSACCIÓN ATÓMICA DE STOCK)
# -----------------------------------------------------------------
@orders_bp.route('', methods=['POST'])
@jwt_required()
def create_order():
    """
    Crea un pedido verificando y descontando stock en una transacción atómica.
    Invalida books:* en Redis y coordina expiración de pedido pendiente.
    Body esperado: {"items": [{"book_id": 1, "quantity": 2}, ...]}
    """
    user_id = g.jwt_user.get('user_id')
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    items_input = data.get('items', [])

    if not items_input or not isinstance(items_input, list):
        return make_response_format({
            'status': 'error',
            'message': 'Debe enviar un arreglo de items: [{"book_id": int, "quantity": int}]'
        }, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                subtotal = Decimal('0.00')
                processed_items = []

                # Validar y reservar stock bloqueando filas con FOR UPDATE
                for item in items_input:
                    book_id = int(item.get('book_id', 0))
                    qty = int(item.get('quantity', 0))

                    if book_id <= 0 or qty <= 0:
                        return make_response_format({
                            'status': 'error',
                            'message': f'Item inválido: book_id={book_id}, quantity={qty}. Deben ser mayores a 0.'
                        }, 400, request)

                    cur.execute(
                        "SELECT id, title, price, stock FROM books WHERE id = %s FOR UPDATE",
                        (book_id,)
                    )
                    book = cur.fetchone()

                    if not book:
                        return make_response_format({
                            'status': 'error',
                            'message': f'Libro con ID {book_id} no existe en el catálogo.'
                        }, 404, request)

                    available_stock = int(book['stock'])
                    if available_stock < qty:
                        return make_response_format({
                            'status': 'error',
                            'message': (
                                f"Stock insuficiente para '{book['title']}' (ID {book_id}). "
                                f"Disponible: {available_stock}, Solicitado: {qty}."
                            )
                        }, 400, request)

                    unit_price = Decimal(str(book['price']))
                    line_total = unit_price * qty
                    subtotal += line_total

                    processed_items.append({
                        'book_id': book_id,
                        'title': book['title'],
                        'unit_price': unit_price,
                        'quantity': qty,
                        'line_total': line_total
                    })

                total = subtotal  # Puede agregarse impuestos/envío si se requiere

                # 1. Insertar orden en status 'pending'
                cur.execute(
                    """INSERT INTO orders (user_id, status, subtotal, total, created_at, updated_at)
                       VALUES (%s, 'pending', %s, %s, now(), now())
                       RETURNING id, created_at""",
                    (user_id, subtotal, total)
                )
                order_row = cur.fetchone()
                order_id = order_row['id']
                created_at = order_row['created_at']

                # 2. Insertar lineas de pedido y descontar stock
                for pi in processed_items:
                    cur.execute(
                        """INSERT INTO order_items (order_id, book_id, title_snapshot, unit_price, quantity, line_total)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (order_id, pi['book_id'], pi['title'], pi['unit_price'], pi['quantity'], pi['line_total'])
                    )
                    cur.execute(
                        "UPDATE books SET stock = stock - %s WHERE id = %s",
                        (pi['quantity'], pi['book_id'])
                    )

                conn.commit()

        # Invalida la caché de catálogo en Redis (refleja el stock descontado)
        redis_client.invalidate_pattern('books:*')

        # Coordinación temporal en Redis: marcar pedido pendiente con expiración (ej. 30 min)
        pending_key = f"order:pending:{order_id}"
        redis_client.set_cache(pending_key, {'user_id': user_id, 'total': float(total)}, ttl=config.ORDER_PENDING_TTL_MINUTES * 60)

        return make_response_format({
            'status': 'success',
            'message': 'Pedido creado exitosamente con stock reservado.',
            'order': {
                'id': order_id,
                'user_id': user_id,
                'status': 'pending',
                'subtotal': float(subtotal),
                'total': float(total),
                'created_at': created_at,
                'items_count': len(processed_items)
            }
        }, 201, request)

    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# PATCH /orders/<id> y PATCH /orders/<id>/status -- ACTUALIZAR ESTADO
# -----------------------------------------------------------------
@orders_bp.route('/<int:order_id>', methods=['PATCH'])
@orders_bp.route('/<int:order_id>/status', methods=['PATCH'])
@jwt_required()
def update_order_status(order_id):
    """
    Actualiza el estado de un pedido ('pending', 'confirmed', 'shipped', 'completed', 'cancelled').
    Si el nuevo estado es 'cancelled', RESTAURA el stock de los libros atómicamente.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_status = (data.get('status') or '').strip().lower()

    valid_statuses = ['pending', 'confirmed', 'shipped', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return make_response_format({
            'status': 'error',
            'message': f"Estado inválido '{new_status}'. Opciones: {', '.join(valid_statuses)}"
        }, 400, request)

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute("SELECT id, user_id, status FROM orders WHERE id = %s FOR UPDATE", (order_id,))
                order = cur.fetchone()

                if not order:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pedido con ID {order_id} no encontrado.'
                    }, 404, request)

                # Si es rol user, solo puede cancelar sus propios pedidos pendientes
                if role != 'admin':
                    if order['user_id'] != user_id:
                        return make_response_format({
                            'status': 'error',
                            'message': 'No autorizado para modificar este pedido.'
                        }, 403, request)
                    if new_status != 'cancelled':
                        return make_response_format({
                            'status': 'error',
                            'message': 'Los usuarios solo tienen permitido cancelar sus pedidos.'
                        }, 403, request)

                current_status = order['status'].lower()

                # Si ya estaba cancelado, evitar doble restauración
                if current_status == 'cancelled':
                    return make_response_format({
                        'status': 'error',
                        'message': 'El pedido ya se encuentra cancelado.'
                    }, 400, request)

                # Si se CANCELA y estaba en 'pending' o 'confirmed': RESTAURAR STOCK
                if new_status == 'cancelled' and current_status in ('pending', 'confirmed'):
                    cur.execute(
                        "SELECT book_id, quantity FROM order_items WHERE order_id = %s",
                        (order_id,)
                    )
                    items = cur.fetchall()
                    for item in items:
                        cur.execute(
                            "UPDATE books SET stock = stock + %s WHERE id = %s",
                            (item['quantity'], item['book_id'])
                        )

                # Actualizar estado de la orden
                cur.execute(
                    "UPDATE orders SET status = %s, updated_at = now() WHERE id = %s",
                    (new_status, order_id)
                )
                conn.commit()

        # Invalida caché de libros en Redis
        redis_client.invalidate_pattern('books:*')
        redis_client.delete_cache(f"order:pending:{order_id}")

        return make_response_format({
            'status': 'success',
            'message': f'Estado del pedido {order_id} actualizado de {current_status} a {new_status}.',
            'order_id': order_id,
            'previous_status': current_status,
            'new_status': new_status
        }, 200, request)

    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)


# -----------------------------------------------------------------
# DELETE /orders/<id> -- CANCELAR/ANULAR PEDIDO Y RESTAURAR STOCK
# -----------------------------------------------------------------
@orders_bp.route('/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    """
    Cancela un pedido mediante DELETE, cambia su estado a 'cancelled',
    restaura atómicamente el stock de cada item en PostgreSQL e invalida books:* en Redis.
    """
    user_id = g.jwt_user.get('user_id')
    role = (g.jwt_user.get('role') or '').lower()

    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                cur.execute("SELECT id, user_id, status FROM orders WHERE id = %s FOR UPDATE", (order_id,))
                order = cur.fetchone()

                if not order:
                    return make_response_format({
                        'status': 'error',
                        'message': f'Pedido con ID {order_id} no encontrado.'
                    }, 404, request)

                # Validar autorización: solo el propio usuario o admin
                if role != 'admin' and order['user_id'] != user_id:
                    return make_response_format({
                        'status': 'error',
                        'message': 'No autorizado para cancelar este pedido.'
                    }, 403, request)

                current_status = order['status'].lower()
                if current_status == 'cancelled':
                    return make_response_format({
                        'status': 'error',
                        'message': 'El pedido ya se encuentra cancelado.'
                    }, 400, request)

                # Restaurar stock si estaba en estado previo activo (pending o confirmed)
                if current_status in ('pending', 'confirmed'):
                    cur.execute(
                        "SELECT book_id, quantity FROM order_items WHERE order_id = %s",
                        (order_id,)
                    )
                    items = cur.fetchall()
                    for item in items:
                        cur.execute(
                            "UPDATE books SET stock = stock + %s WHERE id = %s",
                            (item['quantity'], item['book_id'])
                        )

                # Actualizar orden a cancelled
                cur.execute(
                    "UPDATE orders SET status = 'cancelled', updated_at = now() WHERE id = %s",
                    (order_id,)
                )
                conn.commit()

        # Invalida caché de libros en Redis y clave temporal de orden pendiente
        redis_client.invalidate_pattern('books:*')
        redis_client.delete_cache(f"order:pending:{order_id}")

        return make_response_format({
            'status': 'success',
            'message': f'Pedido {order_id} cancelado exitosamente y stock restaurado.',
            'order_id': order_id,
            'previous_status': current_status,
            'new_status': 'cancelled'
        }, 200, request)

    except Exception as e:
        return make_response_format({'status': 'error', 'message': str(e)}, 500, request)
